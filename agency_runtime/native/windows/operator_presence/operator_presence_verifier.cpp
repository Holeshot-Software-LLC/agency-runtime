#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <sddl.h>
#include <shellapi.h>

#include <UserConsentVerifierInterop.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Security.Credentials.UI.h>
#include <winrt/base.h>

#include <array>
#include <cstddef>
#include <string>
#include <string_view>
#include <vector>

namespace {

using WinrtAsyncStatus = winrt::Windows::Foundation::AsyncStatus;
using winrt::Windows::Foundation::IAsyncOperation;
using winrt::Windows::Security::Credentials::UI::UserConsentVerificationResult;
using winrt::Windows::Security::Credentials::UI::UserConsentVerifier;
using winrt::Windows::Security::Credentials::UI::UserConsentVerifierAvailability;

constexpr DWORD kMaximumRequestBytes = 2'048;
constexpr int kVerifyButtonId = IDOK;
constexpr int kCancelButtonId = IDCANCEL;
constexpr wchar_t kWindowClass[] = L"AgencyRuntimeOperatorPresenceVerifier";
constexpr wchar_t kRollbackWindowTitle[] = L"Agency Runtime - verify roster rollback";
constexpr wchar_t kCodexInstallWindowTitle[] = L"Agency Runtime - verify Codex plugin reinstall";
constexpr std::string_view kProtocol = "AGENCY-OPERATOR-PRESENCE/1";
constexpr std::string_view kRollbackAction = "roster.rollback.v1";
constexpr std::string_view kCodexInstallAction = "install.codex.v1";
constexpr std::string_view kCodexHost = "codex";
constexpr std::string_view kCodexPlugin = "agency-preflight@agency-runtime";
constexpr std::string_view kCodexRecovery =
    "restore-prior-managed-bundle-and-registration";

struct RollbackRequest {
    std::string slug;
    std::string current_version;
    std::string current_hash;
    std::string target_version;
    std::string target_hash;
    std::string authority;
    std::string nonce;
};

struct CodexInstallRequest {
    std::string target_path;
    std::string current_plugin_version;
    std::string candidate_plugin_version;
    std::string current_bundle_sha256;
    std::string candidate_plan_sha256;
    std::string codex_executable_sha256;
    std::string config_revision;
    std::string roster_generation;
    std::string binding_sha256;
    std::string nonce;
};

enum class RequestAction {
    invalid,
    roster_rollback,
    codex_install,
};

struct VerificationRequest {
    RequestAction action = RequestAction::invalid;
    RollbackRequest roster_rollback;
    CodexInstallRequest codex_install;
};

struct WindowState {
    bool verify_requested = false;
    bool cancel_requested = false;
    bool operation_started = false;
};

enum class MutexResult {
    acquired,
    already_running,
    error,
};

struct MutexAcquisition {
    MutexResult result = MutexResult::error;
    winrt::handle handle;
};

int emit_bytes(std::string_view payload, int exit_code) noexcept {
    HANDLE const output = GetStdHandle(STD_OUTPUT_HANDLE);
    if (output == nullptr || output == INVALID_HANDLE_VALUE) {
        return 125;
    }
    if (payload.size() > MAXDWORD) {
        return 125;
    }
    DWORD written = 0;
    BOOL const ok = WriteFile(
        output,
        payload.data(),
        static_cast<DWORD>(payload.size()),
        &written,
        nullptr);
    if (!ok || written != payload.size()) {
        return 125;
    }
    return exit_code;
}

int emit_invalid_input() noexcept {
    return emit_bytes(
        "AGENCY-OPERATOR-PRESENCE/1\n"
        "mode=verification\n"
        "result=invalid-input\n",
        64);
}

int emit_availability(std::string_view result, int exit_code) noexcept {
    try {
        std::string payload{
            "AGENCY-OPERATOR-PRESENCE/1\n"
            "mode=availability\n"
            "result="};
        payload.append(result);
        payload.push_back('\n');
        return emit_bytes(payload, exit_code);
    } catch (...) {
        return 125;
    }
}

int emit_verification(
    RollbackRequest const& request,
    std::string_view result,
    int exit_code) noexcept {
    try {
        std::string payload{
            "AGENCY-OPERATOR-PRESENCE/1\n"
            "mode=verification\n"
            "action=roster.rollback.v1\n"
            "result="};
        payload.append(result);
        payload.append("\nnonce=");
        payload.append(request.nonce);
        payload.push_back('\n');
        return emit_bytes(payload, exit_code);
    } catch (...) {
        return 125;
    }
}

int emit_verification(
    CodexInstallRequest const& request,
    std::string_view result,
    int exit_code) noexcept {
    try {
        std::string payload{
            "AGENCY-OPERATOR-PRESENCE/1\n"
            "mode=verification\n"
            "action=install.codex.v1\n"
            "result="};
        payload.append(result);
        payload.append("\nbinding-sha256=");
        payload.append(request.binding_sha256);
        payload.append("\nnonce=");
        payload.append(request.nonce);
        payload.push_back('\n');
        return emit_bytes(payload, exit_code);
    } catch (...) {
        return 125;
    }
}

enum class InvocationMode {
    verification,
    availability,
    invalid,
};

InvocationMode invocation_mode() noexcept {
    int argc = 0;
    LPWSTR* const argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (argv == nullptr) {
        return InvocationMode::invalid;
    }
    InvocationMode mode = InvocationMode::invalid;
    if (argc == 1) {
        mode = InvocationMode::verification;
    } else if (argc == 2 && lstrcmpW(argv[1], L"--availability-only") == 0) {
        mode = InvocationMode::availability;
    }
    LocalFree(argv);
    return mode;
}

bool is_lower_hex(std::string_view value, std::size_t expected_length) noexcept {
    if (value.size() != expected_length) {
        return false;
    }
    for (char const character : value) {
        if (!((character >= '0' && character <= '9') ||
              (character >= 'a' && character <= 'f'))) {
            return false;
        }
    }
    return true;
}

bool is_slug(std::string_view value) noexcept {
    if (value.size() < 2 || value.size() > 128 ||
        !((value.front() >= 'a' && value.front() <= 'z') ||
          (value.front() >= '0' && value.front() <= '9'))) {
        return false;
    }
    for (char const character : value) {
        bool const allowed =
            (character >= 'a' && character <= 'z') ||
            (character >= '0' && character <= '9') || character == '.' ||
            character == '_' || character == '-';
        if (!allowed) {
            return false;
        }
    }
    return true;
}

bool is_revision(std::string_view value) noexcept {
    return value.size() == 71 && value.starts_with("sha256:") &&
        is_lower_hex(value.substr(7), 64);
}

bool is_plugin_version(std::string_view value) noexcept {
    if (value.empty() || value.size() > 128) {
        return false;
    }
    auto const alphanumeric = [](char character) noexcept {
        return (character >= 'a' && character <= 'z') ||
            (character >= 'A' && character <= 'Z') ||
            (character >= '0' && character <= '9');
    };
    if (!alphanumeric(value.front()) || !alphanumeric(value.back())) {
        return false;
    }
    for (char const character : value) {
        if (!alphanumeric(character) && character != '.' && character != '+' &&
            character != '-') {
            return false;
        }
    }
    return true;
}

bool is_roster_generation(std::string_view value) noexcept {
    if (value.empty() || value.size() > 19 ||
        (value.size() > 1 && value.front() == '0')) {
        return false;
    }
    for (char const character : value) {
        if (character < '0' || character > '9') {
            return false;
        }
    }
    return true;
}

bool is_windows_target_path(std::string_view value) noexcept {
    if (value.size() < 4 || value.size() > 512 || value[0] < 'A' || value[0] > 'Z' ||
        value[1] != ':' || value[2] != '\\' || value.back() == '\\') {
        return false;
    }
    std::size_t component_start = 3;
    for (std::size_t index = 3; index <= value.size(); ++index) {
        if (index < value.size()) {
            char const character = value[index];
            if (character == '/' || character == ':' || character == '<' || character == '>' ||
                character == '"' || character == '|' || character == '?' || character == '*') {
                return false;
            }
            if (character != '\\') {
                continue;
            }
        }
        std::string_view const component = value.substr(component_start, index - component_start);
        if (component.empty() || component == "." || component == ".." ||
            component.back() == ' ' || component.back() == '.') {
            return false;
        }
        component_start = index + 1;
    }
    return true;
}

bool read_stdin(std::string& payload) noexcept {
    HANDLE const input = GetStdHandle(STD_INPUT_HANDLE);
    if (input == nullptr || input == INVALID_HANDLE_VALUE) {
        return false;
    }
    std::array<char, kMaximumRequestBytes + 1> buffer{};
    DWORD used = 0;
    for (;;) {
        DWORD received = 0;
        BOOL const ok = ReadFile(
            input,
            buffer.data() + used,
            static_cast<DWORD>(buffer.size()) - used,
            &received,
            nullptr);
        if (!ok) {
            if (GetLastError() == ERROR_BROKEN_PIPE) {
                break;
            }
            return false;
        }
        if (received == 0) {
            break;
        }
        used += received;
        if (used > kMaximumRequestBytes) {
            return false;
        }
    }
    if (used == 0) {
        return false;
    }
    try {
        payload.assign(buffer.data(), used);
    } catch (...) {
        return false;
    }
    return true;
}

template <std::size_t LineCount>
bool split_exact_lines(
    std::string const& payload,
    std::array<std::string_view, LineCount>& lines) noexcept {
    if (payload.empty() || payload.back() != '\n') {
        return false;
    }
    for (unsigned char const character : payload) {
        if (character != '\n' && (character < 0x20 || character > 0x7e)) {
            return false;
        }
    }
    std::size_t begin = 0;
    for (std::size_t index = 0; index < lines.size(); ++index) {
        std::size_t const end = payload.find('\n', begin);
        if (end == std::string::npos || end == begin) {
            return false;
        }
        lines[index] = std::string_view{payload}.substr(begin, end - begin);
        begin = end + 1;
    }
    return begin == payload.size();
}

bool field(
    std::string_view line,
    std::string_view prefix,
    std::string_view& value) noexcept {
    if (!line.starts_with(prefix)) {
        return false;
    }
    value = line.substr(prefix.size());
    return !value.empty();
}

bool parse_rollback_request(std::string const& payload, RollbackRequest& request) noexcept {
    std::array<std::string_view, 9> lines{};
    if (!split_exact_lines(payload, lines) || lines[0] != kProtocol) {
        return false;
    }
    std::string_view action;
    std::string_view slug;
    std::string_view current_version;
    std::string_view current_hash;
    std::string_view target_version;
    std::string_view target_hash;
    std::string_view authority;
    std::string_view nonce;
    if (!field(lines[1], "action=", action) || action != kRollbackAction ||
        !field(lines[2], "slug=", slug) || !is_slug(slug) ||
        !field(lines[3], "current-version=", current_version) ||
        !is_revision(current_version) ||
        !field(lines[4], "current-hash=", current_hash) ||
        !is_lower_hex(current_hash, 64) ||
        !field(lines[5], "target-version=", target_version) ||
        !is_revision(target_version) ||
        !field(lines[6], "target-hash=", target_hash) ||
        !is_lower_hex(target_hash, 64) ||
        !field(lines[7], "authority=", authority) ||
        (authority != "bundled" && authority != "snapshot") ||
        !field(lines[8], "nonce=", nonce) || !is_lower_hex(nonce, 64)) {
        return false;
    }
    try {
        request.slug.assign(slug);
        request.current_version.assign(current_version);
        request.current_hash.assign(current_hash);
        request.target_version.assign(target_version);
        request.target_hash.assign(target_hash);
        request.authority.assign(authority);
        request.nonce.assign(nonce);
    } catch (...) {
        return false;
    }
    return true;
}

bool parse_codex_install_request(
    std::string const& payload,
    CodexInstallRequest& request) noexcept {
    std::array<std::string_view, 17> lines{};
    if (!split_exact_lines(payload, lines) || lines[0] != kProtocol) {
        return false;
    }
    std::string_view action;
    std::string_view host;
    std::string_view plugin;
    std::string_view target_path;
    std::string_view current_plugin_version;
    std::string_view candidate_plugin_version;
    std::string_view current_bundle_sha256;
    std::string_view candidate_plan_sha256;
    std::string_view codex_executable_sha256;
    std::string_view config_revision;
    std::string_view roster_generation;
    std::string_view will_backup;
    std::string_view will_reregister;
    std::string_view recovery;
    std::string_view binding_sha256;
    std::string_view nonce;
    if (!field(lines[1], "action=", action) || action != kCodexInstallAction ||
        !field(lines[2], "host=", host) || host != kCodexHost ||
        !field(lines[3], "plugin=", plugin) || plugin != kCodexPlugin ||
        !field(lines[4], "target-path=", target_path) ||
        !is_windows_target_path(target_path) ||
        !field(lines[5], "current-plugin-version=", current_plugin_version) ||
        !is_plugin_version(current_plugin_version) ||
        !field(lines[6], "candidate-plugin-version=", candidate_plugin_version) ||
        !is_plugin_version(candidate_plugin_version) ||
        !field(lines[7], "current-bundle-sha256=", current_bundle_sha256) ||
        !is_lower_hex(current_bundle_sha256, 64) ||
        !field(lines[8], "candidate-plan-sha256=", candidate_plan_sha256) ||
        !is_lower_hex(candidate_plan_sha256, 64) ||
        !field(lines[9], "codex-executable-sha256=", codex_executable_sha256) ||
        !is_lower_hex(codex_executable_sha256, 64) ||
        !field(lines[10], "config-revision=", config_revision) ||
        !is_revision(config_revision) ||
        !field(lines[11], "roster-generation=", roster_generation) ||
        !is_roster_generation(roster_generation) ||
        !field(lines[12], "will-backup=", will_backup) || will_backup != "yes" ||
        !field(lines[13], "will-reregister=", will_reregister) ||
        will_reregister != "yes" ||
        !field(lines[14], "recovery=", recovery) || recovery != kCodexRecovery ||
        !field(lines[15], "binding-sha256=", binding_sha256) ||
        !is_lower_hex(binding_sha256, 64) ||
        !field(lines[16], "nonce=", nonce) || !is_lower_hex(nonce, 64)) {
        return false;
    }
    try {
        request.target_path.assign(target_path);
        request.current_plugin_version.assign(current_plugin_version);
        request.candidate_plugin_version.assign(candidate_plugin_version);
        request.current_bundle_sha256.assign(current_bundle_sha256);
        request.candidate_plan_sha256.assign(candidate_plan_sha256);
        request.codex_executable_sha256.assign(codex_executable_sha256);
        request.config_revision.assign(config_revision);
        request.roster_generation.assign(roster_generation);
        request.binding_sha256.assign(binding_sha256);
        request.nonce.assign(nonce);
    } catch (...) {
        return false;
    }
    return true;
}

bool parse_request(VerificationRequest& request) noexcept {
    std::string payload;
    if (!read_stdin(payload)) {
        return false;
    }
    if (parse_rollback_request(payload, request.roster_rollback)) {
        request.action = RequestAction::roster_rollback;
        return true;
    }
    if (parse_codex_install_request(payload, request.codex_install)) {
        request.action = RequestAction::codex_install;
        return true;
    }
    return false;
}

std::wstring widen_ascii(std::string_view value) {
    return std::wstring(value.begin(), value.end());
}

std::wstring verification_message(RollbackRequest const& request) {
    std::wstring message{
        L"Agency Runtime roster rollback\n\n"
        L"Specialist: "};
    message.append(widen_ascii(request.slug));
    message.append(L"\nCurrent revision: ");
    message.append(widen_ascii(request.current_version));
    message.append(L"\nCurrent content hash: ");
    message.append(widen_ascii(request.current_hash));
    message.append(L"\nTarget revision: ");
    message.append(widen_ascii(request.target_version));
    message.append(L"\nTarget content hash: ");
    message.append(widen_ascii(request.target_hash));
    message.append(L"\nActivation authority: ");
    message.append(widen_ascii(request.authority));
    message.append(
        L"\n\nConsequence: restore the full authoritative roster projection from this "
        L"reviewed target revision: name, division, description, source provenance, prompt "
        L"content and path, categories, capabilities, tool affinity, and workforce routing "
        L"contract while preserving current worker lifecycle (employment and standing). "
        L"Agency Runtime will re-check the displayed activation authority and every identity, "
        L"append rollback audit history, and advance roster generation before committing.");
    return message;
}

std::wstring verification_message(CodexInstallRequest const& request) {
    std::wstring message{
        L"Agency Runtime Codex plugin reinstall\n\n"
        L"Target host: Codex\nPlugin: agency-preflight@agency-runtime\nManaged marketplace: "};
    message.append(widen_ascii(request.target_path));
    message.append(L"\nCurrent plugin: ");
    message.append(widen_ascii(request.current_plugin_version));
    message.append(L"\nCandidate plugin: ");
    message.append(widen_ascii(request.candidate_plugin_version));
    message.append(L"\nCandidate transaction plan SHA-256: ");
    message.append(widen_ascii(request.candidate_plan_sha256));
    message.append(L"\nCodex executable SHA-256: ");
    message.append(widen_ascii(request.codex_executable_sha256));
    message.append(L"\nConfiguration revision: ");
    message.append(widen_ascii(request.config_revision));
    message.append(L"\nRoster generation: ");
    message.append(widen_ascii(request.roster_generation));
    message.append(
        L"\n\nThe transaction plan digest binds the generated component bytes plus the "
        L"immutable launcher-publication plan. The published bundle is re-attested before "
        L"installation. Consequence: create an owner-private backup, replace only the managed Agency "
        L"Runtime Codex marketplace bundle, and remove then re-add only the Agency plugin "
        L"registration. The roster, runtime controls, dashboard, Codex authentication, and "
        L"all other plugins remain unchanged. On failure Agency Runtime restores the prior "
        L"managed bundle and prior Agency plugin registration or reports incomplete recovery. "
        L"This does not grant hook trust, prove the plugin loaded, prove a canary, or establish "
        L"production publisher trust.");
    return message;
}

MutexAcquisition acquire_user_session_mutex() noexcept {
    try {
        winrt::handle token;
        HANDLE raw_token = nullptr;
        if (!OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &raw_token)) {
            return {};
        }
        token.attach(raw_token);
        DWORD required = 0;
        BOOL const initial = GetTokenInformation(token.get(), TokenUser, nullptr, 0, &required);
        if (initial || GetLastError() != ERROR_INSUFFICIENT_BUFFER || required == 0) {
            return {};
        }
        std::vector<unsigned char> bytes(required);
        if (!GetTokenInformation(token.get(), TokenUser, bytes.data(), required, &required)) {
            return {};
        }
        auto const user = reinterpret_cast<TOKEN_USER const*>(bytes.data());
        LPWSTR sid_text = nullptr;
        if (!ConvertSidToStringSidW(user->User.Sid, &sid_text) || sid_text == nullptr) {
            return {};
        }
        std::wstring name{L"Local\\AgencyRuntime.OperatorPresence."};
        name.append(sid_text);
        LocalFree(sid_text);
        SetLastError(ERROR_SUCCESS);
        HANDLE const raw_mutex = CreateMutexW(nullptr, FALSE, name.c_str());
        DWORD const create_error = GetLastError();
        if (raw_mutex == nullptr) {
            return {};
        }
        MutexAcquisition acquisition;
        acquisition.handle.attach(raw_mutex);
        acquisition.result = create_error == ERROR_ALREADY_EXISTS
            ? MutexResult::already_running
            : MutexResult::acquired;
        return acquisition;
    } catch (...) {
        return {};
    }
}

void set_control_font(HWND control) noexcept {
    HFONT const font = static_cast<HFONT>(GetStockObject(DEFAULT_GUI_FONT));
    if (font != nullptr) {
        SendMessageW(control, WM_SETFONT, reinterpret_cast<WPARAM>(font), TRUE);
    }
}

HWND create_static(
    HWND parent,
    std::wstring const& text,
    int x,
    int y,
    int width,
    int height) noexcept {
    HWND const control = CreateWindowExW(
        0,
        L"STATIC",
        text.c_str(),
        WS_CHILD | WS_VISIBLE | SS_LEFT | SS_NOPREFIX,
        x,
        y,
        width,
        height,
        parent,
        nullptr,
        GetModuleHandleW(nullptr),
        nullptr);
    if (control != nullptr) {
        set_control_font(control);
    }
    return control;
}

HWND create_button(
    HWND parent,
    wchar_t const* text,
    int identifier,
    int x,
    int y,
    int width,
    bool default_button) noexcept {
    HWND const control = CreateWindowExW(
        0,
        L"BUTTON",
        text,
        WS_CHILD | WS_VISIBLE | WS_TABSTOP |
            (default_button ? BS_DEFPUSHBUTTON : BS_PUSHBUTTON),
        x,
        y,
        width,
        36,
        parent,
        reinterpret_cast<HMENU>(static_cast<INT_PTR>(identifier)),
        GetModuleHandleW(nullptr),
        nullptr);
    if (control != nullptr) {
        set_control_font(control);
    }
    return control;
}

LRESULT CALLBACK window_procedure(
    HWND window,
    UINT message,
    WPARAM wparam,
    LPARAM lparam) noexcept {
    WindowState* state = reinterpret_cast<WindowState*>(
        GetWindowLongPtrW(window, GWLP_USERDATA));
    if (message == WM_NCCREATE) {
        auto const creation = reinterpret_cast<CREATESTRUCTW const*>(lparam);
        state = static_cast<WindowState*>(creation->lpCreateParams);
        SetWindowLongPtrW(window, GWLP_USERDATA, reinterpret_cast<LONG_PTR>(state));
    }
    if (state != nullptr && message == WM_COMMAND) {
        int const identifier = LOWORD(wparam);
        if (identifier == kVerifyButtonId && !state->operation_started) {
            state->verify_requested = true;
            EnableWindow(GetDlgItem(window, kVerifyButtonId), FALSE);
            EnableWindow(GetDlgItem(window, kCancelButtonId), FALSE);
            return 0;
        }
        if (identifier == kCancelButtonId && !state->operation_started) {
            state->cancel_requested = true;
            return 0;
        }
    }
    if (state != nullptr && message == WM_CLOSE) {
        if (!state->operation_started) {
            state->cancel_requested = true;
        }
        return 0;
    }
    return DefWindowProcW(window, message, wparam, lparam);
}

HWND create_verification_window(
    HINSTANCE instance,
    RollbackRequest const& request,
    WindowState& state) noexcept {
    WNDCLASSEXW window_class{};
    window_class.cbSize = sizeof(window_class);
    window_class.lpfnWndProc = window_procedure;
    window_class.hInstance = instance;
    window_class.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    window_class.hbrBackground = reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1);
    window_class.lpszClassName = kWindowClass;
    if (RegisterClassExW(&window_class) == 0 &&
        GetLastError() != ERROR_CLASS_ALREADY_EXISTS) {
        return nullptr;
    }
    HWND const window = CreateWindowExW(
        WS_EX_CONTROLPARENT | WS_EX_DLGMODALFRAME,
        kWindowClass,
        kRollbackWindowTitle,
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU,
        CW_USEDEFAULT,
        CW_USEDEFAULT,
        940,
        580,
        nullptr,
        nullptr,
        instance,
        &state);
    if (window == nullptr) {
        return nullptr;
    }
    try {
        std::wstring slug = L"Specialist: ";
        std::wstring const slug_value = widen_ascii(request.slug);
        constexpr size_t slug_wrap = 64;
        slug.append(slug_value.substr(0, slug_wrap));
        if (slug_value.size() > slug_wrap) {
            slug.append(L"\r\n");
            slug.append(slug_value.substr(slug_wrap));
        }
        std::wstring const current_version =
            L"Current revision: " + widen_ascii(request.current_version);
        std::wstring const current_hash =
            L"Current content hash: " + widen_ascii(request.current_hash);
        std::wstring const target_version =
            L"Target revision: " + widen_ascii(request.target_version);
        std::wstring const target_hash =
            L"Target content hash: " + widen_ascii(request.target_hash);
        std::wstring const authority =
            L"Activation authority: " + widen_ascii(request.authority);
        bool const controls_created =
            create_static(
                window,
                L"Verify roster rollback",
                24,
                20,
                870,
                24) != nullptr &&
            create_static(
                window,
                L"Review the exact immutable identities below. Selecting Verify opens "
                L"Windows Hello.",
                24,
                52,
                870,
                36) != nullptr &&
            create_static(window, slug, 24, 96, 870, 42) != nullptr &&
            create_static(window, current_version, 24, 146, 870, 22) != nullptr &&
            create_static(window, current_hash, 24, 176, 870, 22) != nullptr &&
            create_static(window, target_version, 24, 216, 870, 22) != nullptr &&
            create_static(window, target_hash, 24, 246, 870, 22) != nullptr &&
            create_static(window, authority, 24, 286, 870, 22) != nullptr &&
            create_static(
                window,
                L"Consequence: restore the full authoritative roster projection from the "
                L"reviewed target: name, division, description, source provenance, prompt "
                L"content/path, categories, capabilities, tool affinity, and workforce "
                L"routing contract while preserving current worker lifecycle (employment "
                L"and standing); append rollback audit history and advance roster generation. "
                L"The displayed activation authority and every identity are re-checked "
                L"before commit.",
                24,
                326,
                870,
                90) != nullptr &&
            create_static(
                window,
                L"Cancel leaves the roster unchanged.",
                24,
                424,
                870,
                22) != nullptr &&
            create_button(window, L"&Verify", kVerifyButtonId, 638, 466, 120, true) != nullptr &&
            create_button(window, L"&Cancel", kCancelButtonId, 774, 466, 120, false) != nullptr;
        if (!controls_created) {
            DestroyWindow(window);
            return nullptr;
        }
    } catch (...) {
        DestroyWindow(window);
        return nullptr;
    }
    ShowWindow(window, SW_SHOWNORMAL);
    UpdateWindow(window);
    SendMessageW(window, DM_SETDEFID, kVerifyButtonId, 0);
    SetFocus(GetDlgItem(window, kVerifyButtonId));
    return window;
}

HWND create_verification_window(
    HINSTANCE instance,
    CodexInstallRequest const& request,
    WindowState& state) noexcept {
    WNDCLASSEXW window_class{};
    window_class.cbSize = sizeof(window_class);
    window_class.lpfnWndProc = window_procedure;
    window_class.hInstance = instance;
    window_class.hCursor = LoadCursorW(nullptr, IDC_ARROW);
    window_class.hbrBackground = reinterpret_cast<HBRUSH>(COLOR_WINDOW + 1);
    window_class.lpszClassName = kWindowClass;
    if (RegisterClassExW(&window_class) == 0 &&
        GetLastError() != ERROR_CLASS_ALREADY_EXISTS) {
        return nullptr;
    }
    HWND const window = CreateWindowExW(
        WS_EX_CONTROLPARENT | WS_EX_DLGMODALFRAME,
        kWindowClass,
        kCodexInstallWindowTitle,
        WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU,
        CW_USEDEFAULT,
        CW_USEDEFAULT,
        1020,
        750,
        nullptr,
        nullptr,
        instance,
        &state);
    if (window == nullptr) {
        return nullptr;
    }
    try {
        std::wstring const target =
            L"Managed marketplace: " + widen_ascii(request.target_path);
        std::wstring const current_version =
            L"Current Agency plugin: " + widen_ascii(request.current_plugin_version);
        std::wstring const current_hash =
            L"Current bundle SHA-256: " + widen_ascii(request.current_bundle_sha256);
        std::wstring const candidate_version =
            L"Candidate Agency plugin: " + widen_ascii(request.candidate_plugin_version);
        std::wstring const candidate_hash =
            L"Candidate transaction plan SHA-256: " + widen_ascii(request.candidate_plan_sha256);
        std::wstring const executable_hash =
            L"Codex executable SHA-256: " + widen_ascii(request.codex_executable_sha256);
        std::wstring const config_revision =
            L"Configuration revision: " + widen_ascii(request.config_revision);
        std::wstring const roster_generation =
            L"Roster generation: " + widen_ascii(request.roster_generation);
        bool const controls_created =
            create_static(
                window,
                L"Verify Codex plugin reinstall",
                24,
                18,
                950,
                24) != nullptr &&
            create_static(
                window,
                L"Review the exact transition below. Selecting Verify reinstall opens "
                L"Windows Hello.",
                24,
                48,
                950,
                34) != nullptr &&
            create_static(window, target, 24, 88, 950, 36) != nullptr &&
            create_static(window, current_version, 24, 130, 950, 22) != nullptr &&
            create_static(window, current_hash, 24, 158, 950, 22) != nullptr &&
            create_static(window, candidate_version, 24, 194, 950, 22) != nullptr &&
            create_static(window, candidate_hash, 24, 222, 950, 22) != nullptr &&
            create_static(window, executable_hash, 24, 258, 950, 22) != nullptr &&
            create_static(window, config_revision, 24, 286, 950, 22) != nullptr &&
            create_static(window, roster_generation, 24, 314, 950, 22) != nullptr &&
            create_static(
                window,
                L"Plan digest: binds generated component bytes plus the immutable launcher-"
                L"publication plan; the published bundle is re-attested before installation.",
                24,
                352,
                950,
                44) != nullptr &&
            create_static(
                window,
                L"Changes: create an owner-private backup; replace only the managed Agency "
                L"Runtime Codex marketplace bundle; remove and re-add only "
                L"agency-preflight@agency-runtime. The roster, runtime controls, dashboard, "
                L"Codex authentication, and every other plugin remain unchanged.",
                24,
                402,
                950,
                78) != nullptr &&
            create_static(
                window,
                L"Recovery: restore the prior managed bundle and prior Agency plugin "
                L"registration. If exact restoration cannot be proven, stop and report "
                L"incomplete recovery. This does not grant hook trust, prove loading or a "
                L"canary, or establish production publisher trust.",
                24,
                490,
                950,
                78) != nullptr &&
            create_static(
                window,
                L"Cancel leaves the current Codex installation unchanged.",
                24,
                578,
                950,
                22) != nullptr &&
            create_button(
                window,
                L"&Verify reinstall",
                kVerifyButtonId,
                658,
                620,
                150,
                true) != nullptr &&
            create_button(window, L"&Cancel", kCancelButtonId, 824, 620, 150, false) != nullptr;
        if (!controls_created) {
            DestroyWindow(window);
            return nullptr;
        }
    } catch (...) {
        DestroyWindow(window);
        return nullptr;
    }
    ShowWindow(window, SW_SHOWNORMAL);
    UpdateWindow(window);
    SendMessageW(window, DM_SETDEFID, kVerifyButtonId, 0);
    SetFocus(GetDlgItem(window, kVerifyButtonId));
    return window;
}

bool pump_until_decision(HWND window, WindowState const& state) noexcept {
    MSG message{};
    while (!state.verify_requested && !state.cancel_requested) {
        BOOL const status = GetMessageW(&message, nullptr, 0, 0);
        if (status <= 0) {
            return false;
        }
        if (message.message == WM_KEYDOWN && message.wParam == VK_ESCAPE) {
            SendMessageW(window, WM_COMMAND, MAKEWPARAM(kCancelButtonId, BN_CLICKED), 0);
        } else if (!IsDialogMessageW(window, &message)) {
            TranslateMessage(&message);
            DispatchMessageW(&message);
        }
    }
    return true;
}

template <typename TResult>
WinrtAsyncStatus wait_for_terminal(
    IAsyncOperation<TResult> const& operation,
    HWND dialog = nullptr) noexcept {
    for (;;) {
        WinrtAsyncStatus const status = operation.Status();
        if (status != WinrtAsyncStatus::Started) {
            return status;
        }
        MsgWaitForMultipleObjectsEx(
            0,
            nullptr,
            50,
            QS_ALLINPUT,
            MWMO_ALERTABLE | MWMO_INPUTAVAILABLE);
        MSG message{};
        while (PeekMessageW(&message, nullptr, 0, 0, PM_REMOVE)) {
            if (dialog != nullptr && message.message == WM_KEYDOWN &&
                message.wParam == VK_ESCAPE) {
                SendMessageW(dialog, WM_COMMAND, MAKEWPARAM(kCancelButtonId, BN_CLICKED), 0);
            } else if (message.message != WM_QUIT &&
                       (dialog == nullptr || !IsDialogMessageW(dialog, &message))) {
                TranslateMessage(&message);
                DispatchMessageW(&message);
            }
        }
    }
}

int availability_result(UserConsentVerifierAvailability value) noexcept {
    switch (value) {
    case UserConsentVerifierAvailability::Available:
        return emit_availability("available", 0);
    case UserConsentVerifierAvailability::DeviceNotPresent:
        return emit_availability("device-not-present", 20);
    case UserConsentVerifierAvailability::NotConfiguredForUser:
        return emit_availability("not-configured", 21);
    case UserConsentVerifierAvailability::DisabledByPolicy:
        return emit_availability("disabled-by-policy", 22);
    case UserConsentVerifierAvailability::DeviceBusy:
        return emit_availability("device-busy", 23);
    default:
        return emit_availability("error", 70);
    }
}

template <typename TRequest>
int verification_result(
    TRequest const& request,
    UserConsentVerificationResult value) noexcept {
    switch (value) {
    case UserConsentVerificationResult::Verified:
        return emit_verification(request, "verified", 0);
    case UserConsentVerificationResult::DeviceNotPresent:
        return emit_verification(request, "device-not-present", 20);
    case UserConsentVerificationResult::NotConfiguredForUser:
        return emit_verification(request, "not-configured", 21);
    case UserConsentVerificationResult::DisabledByPolicy:
        return emit_verification(request, "disabled-by-policy", 22);
    case UserConsentVerificationResult::DeviceBusy:
        return emit_verification(request, "device-busy", 23);
    case UserConsentVerificationResult::RetriesExhausted:
        return emit_verification(request, "retries-exhausted", 24);
    case UserConsentVerificationResult::Canceled:
        return emit_verification(request, "canceled", 25);
    default:
        return emit_verification(request, "error", 70);
    }
}

int run_availability() noexcept {
    try {
        winrt::init_apartment(winrt::apartment_type::single_threaded);
        auto const operation = UserConsentVerifier::CheckAvailabilityAsync();
        WinrtAsyncStatus const status = wait_for_terminal(operation);
        if (status == WinrtAsyncStatus::Completed) {
            return availability_result(operation.GetResults());
        }
        if (status == WinrtAsyncStatus::Canceled) {
            return emit_availability("canceled", 25);
        }
        return emit_availability("error", 70);
    } catch (...) {
        return emit_availability("error", 70);
    }
}

template <typename TRequest>
int run_verification(HINSTANCE instance, TRequest const& request) noexcept {
    MutexAcquisition mutex = acquire_user_session_mutex();
    if (mutex.result == MutexResult::already_running) {
        return emit_verification(request, "already-running", 66);
    }
    if (mutex.result != MutexResult::acquired) {
        return emit_verification(request, "error", 70);
    }
    try {
        winrt::init_apartment(winrt::apartment_type::single_threaded);
        WindowState state;
        HWND const window = create_verification_window(instance, request, state);
        if (window == nullptr) {
            return emit_verification(request, "window-not-active", 65);
        }
        if (!pump_until_decision(window, state)) {
            DestroyWindow(window);
            return emit_verification(request, "error", 70);
        }
        if (state.cancel_requested) {
            DestroyWindow(window);
            return emit_verification(request, "canceled", 25);
        }

        winrt::hstring const message{verification_message(request)};
        auto const interop = winrt::get_activation_factory<
            UserConsentVerifier,
            IUserConsentVerifierInterop>();

        ShowWindow(window, SW_RESTORE);
        BringWindowToTop(window);
        SetActiveWindow(window);
        SetForegroundWindow(window);
        DWORD owner_process = 0;
        DWORD const owner_thread = GetWindowThreadProcessId(window, &owner_process);
        if (!IsWindow(window) || !IsWindowVisible(window) ||
            owner_process != GetCurrentProcessId() || owner_thread != GetCurrentThreadId() ||
            GetForegroundWindow() != window) {
            DestroyWindow(window);
            return emit_verification(request, "window-not-active", 65);
        }

        IAsyncOperation<UserConsentVerificationResult> operation{nullptr};
        winrt::check_hresult(interop->RequestVerificationForWindowAsync(
            window,
            reinterpret_cast<HSTRING>(winrt::get_abi(message)),
            winrt::guid_of<decltype(operation)>(),
            winrt::put_abi(operation)));
        state.operation_started = true;
        WinrtAsyncStatus const status = wait_for_terminal(operation, window);
        // IAsyncInfo::Close is intentionally never called. The window remains
        // alive while the operation is Started; parent Job termination is the
        // only hard-stop path. Local teardown happens only after terminal state.
        state.operation_started = false;
        DestroyWindow(window);
        if (status == WinrtAsyncStatus::Completed) {
            return verification_result(request, operation.GetResults());
        }
        if (status == WinrtAsyncStatus::Canceled) {
            return emit_verification(request, "canceled", 25);
        }
        return emit_verification(request, "error", 70);
    } catch (...) {
        return emit_verification(request, "error", 70);
    }
}

}  // namespace

int WINAPI wWinMain(
    _In_ HINSTANCE instance,
    _In_opt_ HINSTANCE previous_instance,
    _In_ PWSTR command_line,
    _In_ int show_command) {
    UNREFERENCED_PARAMETER(previous_instance);
    UNREFERENCED_PARAMETER(command_line);
    UNREFERENCED_PARAMETER(show_command);
    InvocationMode const mode = invocation_mode();
    if (mode == InvocationMode::invalid) {
        return emit_invalid_input();
    }
    if (mode == InvocationMode::availability) {
        return run_availability();
    }
    VerificationRequest request;
    if (!parse_request(request)) {
        return emit_invalid_input();
    }
    if (request.action == RequestAction::roster_rollback) {
        return run_verification(instance, request.roster_rollback);
    }
    if (request.action == RequestAction::codex_install) {
        return run_verification(instance, request.codex_install);
    }
    return emit_invalid_input();
}

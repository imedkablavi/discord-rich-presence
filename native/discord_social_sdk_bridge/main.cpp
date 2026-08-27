#define DISCORDPP_IMPLEMENTATION
#include "discordpp.h"

#include <atomic>
#include <chrono>
#include <cctype>
#include <cstdint>
#include <iostream>
#include <limits>
#include <memory>
#include <optional>
#include <string>
#include <thread>
#include <unordered_map>
#include <unordered_set>
#include <utility>

namespace {
constexpr std::size_t kMaxLineBytes = 16 * 1024;
constexpr auto kCallbackTimeout = std::chrono::seconds(4);
using Fields = std::unordered_map<std::string, std::string>;

struct UpdateCallbackState {
    std::atomic<bool> finished{false};
    std::atomic<bool> successful{false};
};

enum class ReadStatus { Line, TooLong, Eof };
enum class ApplyResult { Success, Failed, TimedOut };

const std::unordered_set<std::string> kAllowedUpdateFields = {
    "name", "activity_type", "details", "state", "details_url", "state_url",
    "large_image", "large_text", "large_url", "small_image", "small_text",
    "small_url", "start", "end", "button1_label", "button1_url",
    "button2_label", "button2_url"
};

ReadStatus read_bounded_line(std::istream& input, std::string& output) {
    output.clear();
    output.reserve(1024);
    bool saw_any = false;
    bool overflow = false;
    char ch = 0;
    while (input.get(ch)) {
        saw_any = true;
        if (ch == '\n') break;
        if (ch == '\r') continue;
        if (output.size() < kMaxLineBytes) output.push_back(ch);
        else overflow = true;
    }
    if (!saw_any && input.eof()) return ReadStatus::Eof;
    return overflow ? ReadStatus::TooLong : ReadStatus::Line;
}

int hex_value(char ch) {
    if (ch >= '0' && ch <= '9') return ch - '0';
    ch = static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
    if (ch >= 'a' && ch <= 'f') return 10 + (ch - 'a');
    return -1;
}

std::optional<std::string> percent_decode(const std::string& input) {
    std::string output;
    output.reserve(input.size());
    for (std::size_t i = 0; i < input.size(); ++i) {
        if (input[i] != '%') {
            output.push_back(input[i]);
            continue;
        }
        if (i + 2 >= input.size()) return std::nullopt;
        const int hi = hex_value(input[i + 1]);
        const int lo = hex_value(input[i + 2]);
        if (hi < 0 || lo < 0) return std::nullopt;
        const char decoded = static_cast<char>((hi << 4) | lo);
        if (decoded == '\0') return std::nullopt;
        output.push_back(decoded);
        i += 2;
    }
    return output;
}

bool parse_line(const std::string& line, std::string& command, Fields& fields) {
    if (line.empty() || line.size() > kMaxLineBytes) return false;
    fields.clear();
    std::size_t start = 0;
    std::size_t end = line.find('\t');
    command = line.substr(0, end);
    if (command.empty()) return false;
    while (end != std::string::npos) {
        start = end + 1;
        end = line.find('\t', start);
        const std::string item = line.substr(start, end - start);
        const std::size_t equals = item.find('=');
        if (equals == std::string::npos || equals == 0) return false;
        const std::string key = item.substr(0, equals);
        if (fields.find(key) != fields.end()) return false;
        auto decoded = percent_decode(item.substr(equals + 1));
        if (!decoded) return false;
        fields.emplace(key, std::move(*decoded));
    }
    return true;
}

std::optional<std::uint64_t> parse_u64(const std::string& value) {
    if (value.empty()) return std::nullopt;
    try {
        std::size_t consumed = 0;
        const auto parsed = std::stoull(value, &consumed, 10);
        if (consumed != value.size()) return std::nullopt;
        return static_cast<std::uint64_t>(parsed);
    } catch (...) {
        return std::nullopt;
    }
}

std::optional<int> parse_int(const std::string& value) {
    try {
        std::size_t consumed = 0;
        const long parsed = std::stol(value, &consumed, 10);
        if (consumed != value.size() || parsed < std::numeric_limits<int>::min() ||
            parsed > std::numeric_limits<int>::max()) return std::nullopt;
        return static_cast<int>(parsed);
    } catch (...) {
        return std::nullopt;
    }
}

const std::string* field(const Fields& fields, const char* key) {
    const auto it = fields.find(key);
    return it == fields.end() ? nullptr : &it->second;
}

bool valid_update_fields(const Fields& fields) {
    for (const auto& item : fields) {
        if (kAllowedUpdateFields.find(item.first) == kAllowedUpdateFields.end()) return false;
    }
    return true;
}

void print_ok() { std::cout << "OK\n" << std::flush; }
void print_error(const char* code) {
    std::cout << "ERR\tcode=" << code << "\n" << std::flush;
}

ApplyResult apply_activity(const std::shared_ptr<discordpp::Client>& client, const Fields& fields) {
    if (!valid_update_fields(fields)) return ApplyResult::Failed;
    const std::string* name = field(fields, "name");
    if (!name || name->size() < 2 || name->size() > 128) return ApplyResult::Failed;

    discordpp::Activity activity{};
    activity.SetName(*name);

    if (const auto* raw = field(fields, "activity_type")) {
        auto parsed = parse_int(*raw);
        if (!parsed || *parsed < 0 || *parsed > 6) return ApplyResult::Failed;
        activity.SetType(static_cast<discordpp::ActivityTypes>(*parsed));
    }
    if (const auto* value = field(fields, "details")) activity.SetDetails(*value);
    if (const auto* value = field(fields, "state")) activity.SetState(*value);
    if (const auto* value = field(fields, "details_url")) activity.SetDetailsUrl(*value);
    if (const auto* value = field(fields, "state_url")) activity.SetStateUrl(*value);

    const bool has_assets = field(fields, "large_image") || field(fields, "large_text") ||
        field(fields, "large_url") || field(fields, "small_image") ||
        field(fields, "small_text") || field(fields, "small_url");
    if (has_assets) {
        discordpp::ActivityAssets assets{};
        if (const auto* value = field(fields, "large_image")) assets.SetLargeImage(*value);
        if (const auto* value = field(fields, "large_text")) assets.SetLargeText(*value);
        if (const auto* value = field(fields, "large_url")) assets.SetLargeUrl(*value);
        if (const auto* value = field(fields, "small_image")) assets.SetSmallImage(*value);
        if (const auto* value = field(fields, "small_text")) assets.SetSmallText(*value);
        if (const auto* value = field(fields, "small_url")) assets.SetSmallUrl(*value);
        activity.SetAssets(assets);
    }

    const auto* start_raw = field(fields, "start");
    const auto* end_raw = field(fields, "end");
    if (start_raw || end_raw) {
        discordpp::ActivityTimestamps timestamps{};
        if (start_raw) {
            auto value = parse_u64(*start_raw);
            if (!value) return ApplyResult::Failed;
            timestamps.SetStart(*value);
        }
        if (end_raw) {
            auto value = parse_u64(*end_raw);
            if (!value) return ApplyResult::Failed;
            timestamps.SetEnd(*value);
        }
        activity.SetTimestamps(timestamps);
    }

    for (int index = 1; index <= 2; ++index) {
        const std::string label_key = "button" + std::to_string(index) + "_label";
        const std::string url_key = "button" + std::to_string(index) + "_url";
        const auto* label = field(fields, label_key.c_str());
        const auto* url = field(fields, url_key.c_str());
        if (!label && !url) continue;
        if (!label || !url) return ApplyResult::Failed;
        discordpp::ActivityButton button{};
        button.SetLabel(*label);
        button.SetUrl(*url);
        activity.AddButton(button);
    }

    // The SDK owns the asynchronous callback until it either fires or its
    // client is destroyed. Keep callback state on the heap and capture it by
    // value so a late callback after our timeout can never reference stack
    // memory that has already gone out of scope.
    auto callback_state = std::make_shared<UpdateCallbackState>();
    client->UpdateRichPresence(std::move(activity), [callback_state](discordpp::ClientResult result) {
        callback_state->successful.store(result.Successful(), std::memory_order_relaxed);
        callback_state->finished.store(true, std::memory_order_release);
    });

    const auto deadline = std::chrono::steady_clock::now() + kCallbackTimeout;
    while (!callback_state->finished.load(std::memory_order_acquire) &&
           std::chrono::steady_clock::now() < deadline) {
        discordpp::RunCallbacks();
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
    discordpp::RunCallbacks();
    if (!callback_state->finished.load(std::memory_order_acquire)) return ApplyResult::TimedOut;
    return callback_state->successful.load(std::memory_order_relaxed)
        ? ApplyResult::Success
        : ApplyResult::Failed;
}

std::shared_ptr<discordpp::Client> make_client(std::uint64_t application_id) {
    auto client = std::make_shared<discordpp::Client>();
    client->SetApplicationId(application_id);
    return client;
}
}  // namespace

int main() {
    std::shared_ptr<discordpp::Client> client = std::make_shared<discordpp::Client>();
    std::optional<std::uint64_t> application_id;
    std::string line;

    while (true) {
        const ReadStatus status = read_bounded_line(std::cin, line);
        if (status == ReadStatus::Eof) break;
        if (status == ReadStatus::TooLong) {
            print_error("line_too_large");
            continue;
        }

        std::string command;
        Fields fields;
        if (!parse_line(line, command, fields)) {
            print_error("invalid_protocol");
            continue;
        }

        if (command == "PING") {
            if (fields.empty()) print_ok(); else print_error("unexpected_fields");
            continue;
        }
        if (command == "SET_APP") {
            if (fields.size() != 1 || !field(fields, "application_id")) {
                print_error("invalid_application_id");
                continue;
            }
            auto parsed = parse_u64(*field(fields, "application_id"));
            if (!parsed || *parsed == 0) {
                print_error("invalid_application_id");
                continue;
            }
            application_id = *parsed;
            client = make_client(*application_id);
            print_ok();
            continue;
        }
        if (command == "CLEAR") {
            if (!application_id || !fields.empty()) {
                print_error(!application_id ? "application_not_set" : "unexpected_fields");
                continue;
            }
            client->ClearRichPresence();
            discordpp::RunCallbacks();
            print_ok();
            continue;
        }
        if (command == "UPDATE") {
            if (!application_id) {
                print_error("application_not_set");
                continue;
            }
            const ApplyResult result = apply_activity(client, fields);
            if (result == ApplyResult::Success) {
                print_ok();
            } else if (result == ApplyResult::TimedOut) {
                // A timed-out async callback may retain SDK-owned pending state.
                // Recreate the client before accepting another update so repeated
                // desktop RPC failures cannot accumulate memory indefinitely.
                client = make_client(*application_id);
                print_error("update_timeout");
            } else {
                print_error("update_failed");
            }
            continue;
        }
        if (command == "QUIT") {
            if (!fields.empty()) {
                print_error("unexpected_fields");
                continue;
            }
            if (application_id) {
                client->ClearRichPresence();
                discordpp::RunCallbacks();
            }
            print_ok();
            break;
        }
        print_error("unsupported_command");
    }
    return 0;
}

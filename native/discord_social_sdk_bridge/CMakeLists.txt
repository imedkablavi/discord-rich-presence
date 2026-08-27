cmake_minimum_required(VERSION 3.16)
project(cybrex_discord_social_sdk_bridge LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(DISCORD_SOCIAL_SDK_ROOT "" CACHE PATH "Path to the extracted Discord Social SDK C++ archive")
if(NOT DISCORD_SOCIAL_SDK_ROOT)
    message(FATAL_ERROR "Set DISCORD_SOCIAL_SDK_ROOT to the extracted Discord Social SDK directory")
endif()

set(DISCORD_SDK_INCLUDE_DIR "${DISCORD_SOCIAL_SDK_ROOT}/include")
set(DISCORD_SDK_LIB_DIR "${DISCORD_SOCIAL_SDK_ROOT}/lib/release")
set(DISCORD_SDK_BIN_DIR "${DISCORD_SOCIAL_SDK_ROOT}/bin/release")

if(NOT EXISTS "${DISCORD_SDK_INCLUDE_DIR}/discordpp.h")
    message(FATAL_ERROR "discordpp.h not found under ${DISCORD_SDK_INCLUDE_DIR}")
endif()

add_executable(cybrex-discord-social-sdk main.cpp)
target_include_directories(cybrex-discord-social-sdk PRIVATE "${DISCORD_SDK_INCLUDE_DIR}")

if(WIN32)
    set(DISCORD_SDK_LINK "${DISCORD_SDK_LIB_DIR}/discord_partner_sdk.lib")
    set(DISCORD_SDK_RUNTIME "${DISCORD_SDK_BIN_DIR}/discord_partner_sdk.dll")
elseif(APPLE)
    set(DISCORD_SDK_LINK "${DISCORD_SDK_LIB_DIR}/libdiscord_partner_sdk.dylib")
    set(DISCORD_SDK_RUNTIME "${DISCORD_SDK_LIB_DIR}/libdiscord_partner_sdk.dylib")
else()
    set(DISCORD_SDK_LINK "${DISCORD_SDK_LIB_DIR}/libdiscord_partner_sdk.so")
    set(DISCORD_SDK_RUNTIME "${DISCORD_SDK_LIB_DIR}/libdiscord_partner_sdk.so")
    set_target_properties(cybrex-discord-social-sdk PROPERTIES BUILD_RPATH "$ORIGIN")
endif()

if(NOT EXISTS "${DISCORD_SDK_LINK}")
    message(FATAL_ERROR "Discord Social SDK link library not found: ${DISCORD_SDK_LINK}")
endif()
if(NOT EXISTS "${DISCORD_SDK_RUNTIME}")
    message(FATAL_ERROR "Discord Social SDK runtime not found: ${DISCORD_SDK_RUNTIME}")
endif()

target_link_libraries(cybrex-discord-social-sdk PRIVATE "${DISCORD_SDK_LINK}")

add_custom_command(TARGET cybrex-discord-social-sdk POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E copy_if_different
        "${DISCORD_SDK_RUNTIME}"
        "$<TARGET_FILE_DIR:cybrex-discord-social-sdk>"
    VERBATIM
)

if(MSVC)
    target_compile_options(cybrex-discord-social-sdk PRIVATE /W4 /permissive-)
else()
    target_compile_options(cybrex-discord-social-sdk PRIVATE -Wall -Wextra -Wpedantic)
endif()

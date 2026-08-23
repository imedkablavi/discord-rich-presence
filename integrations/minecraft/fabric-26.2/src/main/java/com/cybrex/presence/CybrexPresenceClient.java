package com.cybrex.presence;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.Properties;

import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.loader.api.FabricLoader;

import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ServerData;

public final class CybrexPresenceClient implements ClientModInitializer {
    private static final int DEFAULT_PORT = 32194;
    private static final int SEND_INTERVAL_TICKS = 100;
    private static final HttpClient HTTP = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(1))
        .build();

    private int tickCounter;
    private int port = DEFAULT_PORT;
    private boolean sendServerName;

    @Override
    public void onInitializeClient() {
        loadConfig();
        ClientTickEvents.END_CLIENT_TICK.register(this::onEndTick);
    }

    private void onEndTick(Minecraft client) {
        if (client.player == null || client.level == null) {
            tickCounter = 0;
            return;
        }

        tickCounter++;
        if (tickCounter < SEND_INTERVAL_TICKS) {
            return;
        }
        tickCounter = 0;

        String mode = client.hasSingleplayerServer() ? "Singleplayer" : "Multiplayer";
        String dimension = client.level.dimension().identifier().toString();
        String serverName = "";
        if (sendServerName) {
            ServerData server = client.getCurrentServer();
            if (server != null && server.name != null) {
                serverName = server.name;
            }
        }

        sendSnapshot(mode, dimension, serverName);
    }

    private void sendSnapshot(String mode, String dimension, String serverName) {
        String json = "{" +
            "\"mode\":\"" + jsonEscape(mode) + "\"," +
            "\"dimension\":\"" + jsonEscape(dimension) + "\"," +
            "\"server_name\":\"" + jsonEscape(serverName) + "\"" +
            "}";

        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create("http://127.0.0.1:" + port + "/presence"))
            .timeout(Duration.ofSeconds(1))
            .header("Content-Type", "application/json")
            .header("X-CYBREX-Companion", "minecraft-fabric-1")
            .POST(HttpRequest.BodyPublishers.ofString(json, StandardCharsets.UTF_8))
            .build();

        HTTP.sendAsync(request, HttpResponse.BodyHandlers.discarding())
            .exceptionally(ignored -> null);
    }

    private void loadConfig() {
        Path configPath = FabricLoader.getInstance().getConfigDir()
            .resolve("cybrex-presence.properties");
        Properties properties = new Properties();
        properties.setProperty("port", Integer.toString(DEFAULT_PORT));
        properties.setProperty("send_server_name", "false");

        if (Files.isRegularFile(configPath)) {
            try (InputStream input = Files.newInputStream(configPath)) {
                properties.load(input);
            } catch (IOException ignored) {
                // Privacy-safe defaults remain active when the config is unreadable.
            }
        } else {
            try {
                Files.createDirectories(configPath.getParent());
                try (OutputStream output = Files.newOutputStream(configPath)) {
                    properties.store(output,
                        "CYBREX Presence Companion. Server names are disabled by default.");
                }
            } catch (IOException ignored) {
                // The companion still works with privacy-safe in-memory defaults.
            }
        }

        port = parsePort(properties.getProperty("port"));
        sendServerName = "true".equalsIgnoreCase(
            properties.getProperty("send_server_name", "false").trim()
        );
    }

    private static int parsePort(String value) {
        try {
            int parsed = Integer.parseInt(value == null ? "" : value.trim());
            if (parsed >= 1024 && parsed <= 65535) {
                return parsed;
            }
        } catch (NumberFormatException ignored) {
            // Fall through to the fixed safe default.
        }
        return DEFAULT_PORT;
    }

    private static String jsonEscape(String value) {
        String text = value == null ? "" : value;
        StringBuilder result = new StringBuilder(Math.min(text.length() + 16, 256));
        for (int i = 0; i < text.length() && result.length() < 128; i++) {
            char ch = text.charAt(i);
            switch (ch) {
                case '\\' -> result.append("\\\\");
                case '"' -> result.append("\\\"");
                case '\n', '\r', '\t' -> result.append(' ');
                default -> {
                    if (ch >= 0x20) {
                        result.append(ch);
                    }
                }
            }
        }
        return result.toString();
    }
}

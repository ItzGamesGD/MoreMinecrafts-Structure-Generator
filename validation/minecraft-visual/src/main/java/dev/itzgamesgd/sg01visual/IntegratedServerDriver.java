package dev.itzgamesgd.sg01visual;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.Minecraft;
import net.minecraft.client.server.IntegratedServer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Test-only driver for the integrated-server checks (N10-R): replays a command file line by line once the client is in a world.
 * A line starting with "/" is sent as a chat command by the player (the host, so it needs cheats enabled in the world); "!info" logs the integrated server state;
 * "!stop" stops the client gracefully (which stops the integrated server and fires the module's shutdown report). One line is handled every 40 ticks.
 */
public final class IntegratedServerDriver implements ClientModInitializer {
    private static final Logger LOGGER = LoggerFactory.getLogger("sg01-visual");
    private static int done;
    private static int cooldown = 100;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            String file = System.getenv("SG01_IT_COMMANDS");
            if (file == null || file.isBlank() || client.player == null || client.level == null || --cooldown > 0) return;
            try {
                Path path = Path.of(file);
                if (!Files.isRegularFile(path)) return;
                List<String> lines = Files.readAllLines(path);
                if (done >= lines.size()) return;
                String line = lines.get(done++).trim();
                cooldown = 40;
                if (line.startsWith("/")) {
                    client.getConnection().sendCommand(line.substring(1));
                } else if (line.equals("!info")) {
                    IntegratedServer server = client.getSingleplayerServer();
                    LOGGER.info("SG01_IT_INFO singleplayer={} published={} port={}", client.hasSingleplayerServer(), server != null && server.isPublished(), server == null ? -1 : server.getPort());
                } else if (line.equals("!stop")) {
                    LOGGER.info("SG01_IT_STOP");
                    client.stop();
                    return;
                }
                LOGGER.info("SG01_IT_DONE {} {}", done, line);
            } catch (Exception error) {
                LOGGER.error("SG01_IT_FAILED", error);
            }
        });
    }
}

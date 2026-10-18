package dev.itzgamesgd.sg01visual;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.regex.Pattern;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.rendering.v1.hud.HudElementRegistry;
import net.fabricmc.fabric.api.client.rendering.v1.hud.VanillaHudElements;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.resources.Identifier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Test-only native Minecraft screenshot capture, adapted from the proven 26.3 arena harness. */
public final class ScreenshotCaptureHarness implements ClientModInitializer {
    private static final Logger LOGGER = LoggerFactory.getLogger("sg01-visual");
    private static final Pattern SAFE_PNG_NAME = Pattern.compile("[a-zA-Z0-9._-]+\\.png");
    private static boolean joined;
    private static boolean capturing;
    private static String pendingName;
    private static int settleFrames;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(client -> {
            if (!joined && client.player != null && client.level != null) {
                joined = true;
                LOGGER.info("SG01_CLIENT_JOINED");
            }
        });

        HudElementRegistry.attachElementAfter(
                VanillaHudElements.CHAT,
                Identifier.parse("sg01visual:capture_frame"),
                (graphics, delta) -> captureRequestedFrame());
    }

    private static void captureRequestedFrame() {
        if (!joined || capturing) return;
        String requestValue = System.getenv("SG01_SCREENSHOT_REQUEST");
        if (requestValue == null || requestValue.isBlank()) return;
        Path request = Path.of(requestValue);
        if (!Files.isRegularFile(request)) return;

        try {
            String name = Files.readString(request).trim();
            if (!SAFE_PNG_NAME.matcher(name).matches()) {
                LOGGER.error("SG01_CAPTURE_FAILED unsafe screenshot name in {}", request);
                return;
            }
            if (!name.equals(pendingName)) {
                pendingName = name;
                settleFrames = 30;
            }
            if (--settleFrames > 0) return;

            Minecraft client = Minecraft.getInstance();
            if (client.player == null || client.level == null || client.gui.screen() != null) return;
            capturing = true;
            Path destination = client.gameDirectory.toPath().resolve("screenshots").resolve(name);
            Screenshot.grab(client.gameDirectory, name, client.gameRenderer.mainRenderTarget(), 1, message -> {
                try {
                    if (!Files.isRegularFile(destination) || Files.size(destination) == 0) {
                        throw new IllegalStateException(message.getString());
                    }
                    Files.deleteIfExists(request);
                    LOGGER.info("SG01_CAPTURE_WRITTEN name={} bytes={}", name, Files.size(destination));
                } catch (Exception error) {
                    LOGGER.error("SG01_CAPTURE_FAILED name={}", name, error);
                } finally {
                    capturing = false;
                    pendingName = null;
                }
            });
        } catch (Exception error) {
            LOGGER.error("SG01_CAPTURE_FAILED reading request {}", request, error);
        }
    }
}

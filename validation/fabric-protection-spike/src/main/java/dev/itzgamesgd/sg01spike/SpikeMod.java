package dev.itzgamesgd.sg01spike;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.stream.Collectors;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.world.level.levelgen.feature.GeodeFeature;
import net.minecraft.world.level.levelgen.feature.MonsterRoomFeature;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** N7-A experimental spike entrypoint: configuration, hook verification, report. */
public final class SpikeMod implements ModInitializer {
    public static final Logger LOGGER = LoggerFactory.getLogger("sg01-spike");

    @Override
    public void onInitialize() {
        LOGGER.info("SG_SPIKE mode={} fixture={} refine={} oracle={} features={}", Guard.MODE, Guard.FIXTURE, Guard.REFINE, Guard.ORACLE_MONSTER_ROOM ? "monster_room" : "off",
                System.getenv().getOrDefault("SG01_FEATURES", "both"));
        if (Guard.FIXTURE != Guard.Fixture.NONE) {
            LOGGER.warn("SG_SPIKE EXPERIMENT FIXTURE {} active: causal attribution only, never ship", Guard.FIXTURE);
        }
        // Spawn-area chunks are generated before SERVER_STARTED, so the configuration must be resolved at SERVER_STARTING.
        ServerLifecycleEvents.SERVER_STARTING.register(server -> {
            verifyHooks();
            ProtectionConfig.resolve(server);
        });
        ServerLifecycleEvents.END_DATA_PACK_RELOAD.register((server, resources, success) -> {
            if (success) ProtectionConfig.resolve(server);
        });
        ServerLifecycleEvents.SERVER_STOPPING.register(server -> writeReport());
    }

    /** The marker interface is only present on the target records if both Mixins were applied. */
    private static void verifyHooks() {
        boolean geode = GuardMarker.class.isAssignableFrom(GeodeFeature.class);
        boolean room = GuardMarker.class.isAssignableFrom(MonsterRoomFeature.class);
        LOGGER.info("SG_SPIKE hook GeodeFeature.place applied={} MonsterRoomFeature.place applied={}", geode, room);
        if (!geode || !room) {
            throw new IllegalStateException("SG protection spike: Mixin not applied (geode=" + geode + ", monster room=" + room + ")");
        }
    }

    private static String stats(GuardStats s) {
        List<String> events = s.events().stream().map(e -> "\"" + e.replace("\\", "\\\\").replace("\"", "'") + "\"").collect(Collectors.toList());
        return String.format("\"%s\":{\"attempts\":%d,\"fast_path\":%d,\"collisions\":%d,\"unavailable\":%d,\"cancelled\":%d,\"would_cancel\":%d,\"not_worldgen\":%d,"
                        + "\"clear\":%d,\"hybrid_skip\":%d,\"shadow_checks\":%d,\"shadow_violations\":%d,\"no_write\":%d,\"oracle_non_air_write\":%d,\"oracle_no_write\":%d,\"oracle_unknown\":%d,\"confusion\":{\"refined\":{\"tp\":%d,\"fp\":%d,\"fn\":%d,\"tn\":%d},\"n7a\":{\"tp\":%d,\"fp\":%d,\"fn\":%d,\"tn\":%d}},\"events\":[%s]}",
                s.feature, s.attempts.get(), s.fastPath.get(), s.collisions.get(), s.unavailable.get(), s.cancelled.get(), s.wouldCancel.get(),
                s.notWorldgen.get(), s.clear.get(), s.hybridSkip.get(), s.shadowChecks.get(), s.shadowViolations.get(), s.noWrite.get(), s.oracleNonAirWrite.get(), s.oracleNoWrite.get(), s.oracleUnknown.get(), s.refinedTp.get(), s.refinedFp.get(), s.refinedFn.get(), s.refinedTn.get(),
                s.n7aTp.get(), s.n7aFp.get(), s.n7aFn.get(), s.n7aTn.get(), String.join(",", events));
    }

    private static void writeReport() {
        String json = "{\"mode\":\"" + Guard.MODE + "\",\"fixture\":\"" + Guard.FIXTURE + "\",\"refine\":\"" + Guard.REFINE + "\",\"shadow\":" + Guard.SHADOW + ",\"oracle\":\""
                + (Guard.ORACLE_MONSTER_ROOM ? "monster_room" : "off") + "\"," + stats(Guard.GEODE) + "," + stats(Guard.MONSTER_ROOM) + ",\"probe\":"
                + Probe.json() + ",\"perf\":" + Perf.json() + "}\n";
        LOGGER.info("SG_SPIKE_REPORT {}", json.replace("\n", ""));
        String path = System.getenv("SG01_SPIKE_REPORT");
        if (path != null && !path.isBlank()) {
            try {
                Files.writeString(Path.of(path), json);
            } catch (IOException e) {
                LOGGER.error("SG_SPIKE could not write report", e);
            }
        }
    }
}

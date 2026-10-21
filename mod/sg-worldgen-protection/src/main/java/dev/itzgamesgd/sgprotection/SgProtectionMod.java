package dev.itzgamesgd.sgprotection;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.stream.Collectors;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.loader.api.FabricLoader;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.world.level.levelgen.feature.GeodeFeature;
import net.minecraft.world.level.levelgen.feature.MonsterRoomFeature;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Production entrypoint: hook verification, protection contract, drift guard and shutdown report. */
public final class SgProtectionMod implements ModInitializer {
    public static final Logger LOGGER = LoggerFactory.getLogger("sg-protection");

    /** Entrypoint key under which the validation lab mod (never part of the production artifact) registers its {@link LabHooks}. */
    public static final String LAB_ENTRYPOINT = "sg_worldgen_protection:lab";

    @Override
    public void onInitialize() {
        List<LabHooks> labs = FabricLoader.getInstance().getEntrypoints(LAB_ENTRYPOINT, LabHooks.class);
        if (labs.size() > 1) throw new IllegalStateException("SG protection: more than one validation lab mod is installed");
        if (!labs.isEmpty()) {
            LabHooks.install(labs.get(0));
            LOGGER.warn("SG_PROTECTION VALIDATION LAB MOD ACTIVE: lab configuration and instrumentation are enabled; this is not a production configuration");
        }
        LabHooks.Config cfg = LabHooks.get().config();
        LOGGER.info("SG_PROTECTION mode={} fixture={} refine={} oracle={} features={}", cfg.mode(), cfg.fixture(), cfg.refine(), cfg.oracle() ? "monster_room" : "off", cfg.features());
        if (cfg.fixture() != Guard.Fixture.NONE) {
            LOGGER.warn("SG_PROTECTION EXPERIMENT FIXTURE {} active: causal attribution only, never ship", cfg.fixture());
        }
        // Spawn-area chunks are generated before SERVER_STARTED, so the configuration must be resolved at SERVER_STARTING.
        ServerLifecycleEvents.SERVER_STARTING.register(server -> {
            verifyHooks();
            DriftGuard.verifyAtStartup();
            ProtectionConfig.resolve(server);
        });
        ServerLifecycleEvents.END_DATA_PACK_RELOAD.register((server, resources, success) -> {
            if (success) ProtectionConfig.reload(server);
        });
        ServerLifecycleEvents.SERVER_STARTED.register(server -> LabHooks.get().serverStarted(server));
        ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
            LabHooks.get().serverStopping();
            writeReport();
        });
    }

    /** The marker interface is only present on the target records if both Mixins were applied. */
    private static void verifyHooks() {
        boolean geode = GuardMarker.class.isAssignableFrom(GeodeFeature.class);
        boolean room = GuardMarker.class.isAssignableFrom(MonsterRoomFeature.class);
        LOGGER.info("SG_PROTECTION hook GeodeFeature.place applied={} MonsterRoomFeature.place applied={}", geode, room);
        if (!geode || !room) {
            throw new IllegalStateException("SG protection: Mixin not applied (geode=" + geode + ", monster room=" + room + ")");
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

    private static String contractJson() {
        ProtectionContract.Result c = ProtectionConfig.contract;
        String warnings = c == null ? "" : c.warnings().stream().map(w -> "\"" + w.replace("\\", "\\\\").replace("\"", "'") + "\"").collect(Collectors.joining(","));
        String rejected = c == null ? "" : c.rejectedExtensions().stream().map(w -> "\"" + w.replace("\\", "\\\\").replace("\"", "'") + "\"").collect(Collectors.joining(","));
        String last = ProtectionConfig.lastRejection == null ? "null" : "\"" + ProtectionConfig.lastRejection.replace("\\", "\\\\").replace("\"", "'") + "\"";
        return String.format("{\"mode\":\"%s\",\"owner\":%s,\"format\":%d,\"revision\":%d,\"required\":%d,\"extensions\":%d,\"warnings\":[%s],\"rejected_extensions\":[%s],"
                        + "\"reload_rejections\":%d,\"last_rejection\":%s}",
                "manifest", c == null ? "null" : "\"" + c.owner() + "\"", c == null ? 0 : c.format(),
                c == null ? 0 : c.revision(), c == null ? 0 : c.required(), c == null ? 0 : c.extensions(), warnings, rejected, ProtectionConfig.reloadRejections, last);
    }

    private static String driftJson(DriftGuard.State s) {
        String reason = s.reason();
        return String.format("{\"level\":\"%s\",\"fallback\":%b,\"reason\":%s,\"fingerprint\":\"%s\",\"verified_samples\":%d,\"verified_placements\":%d,\"deviations\":%d,\"near_misses\":%d,\"unverified_cancels\":%d,\"promoted_at_attempt\":%d}",
                s.level(), s.level() != DriftGuard.Level.VERIFIED && s.level() != DriftGuard.Level.PROVISIONAL, reason == null ? "null" : "\"" + reason.replace("\\", "\\\\").replace("\"", "'") + "\"",
                s.fingerprint(), s.samples.get(), s.placements.get(), s.deviations.get(), s.nearMisses.get(), s.unverifiedCancels.get(), s.promotedAtAttempt);
    }

    private static String selfCheckJson() {
        return "{\"configured_refine\":\"" + LabHooks.get().config().refine() + "\",\"effective_refine\":\"" + DriftGuard.monsterRoomRefine(LabHooks.get().config().refine()) + "\",\"monster_room\":"
                + driftJson(DriftGuard.MONSTER_ROOM) + ",\"geode\":" + driftJson(DriftGuard.GEODE) + "}";
    }

    private static void writeReport() {
        LabHooks.Config cfg = LabHooks.get().config();
        String json = "{\"mode\":\"" + cfg.mode() + "\",\"fixture\":\"" + cfg.fixture() + "\",\"refine\":\"" + cfg.refine() + "\",\"shadow\":" + cfg.shadow() + ",\"oracle\":\""
                + (cfg.oracle() ? "monster_room" : "off") + "\"," + stats(Guard.GEODE) + "," + stats(Guard.MONSTER_ROOM) + ",\"contract\":" + contractJson()
                + ",\"drift_guard\":" + selfCheckJson() + ",\"lab\":" + (LabHooks.get() != LabHooks.NONE) + LabHooks.get().reportExtras() + "}\n";
        LOGGER.info("SG_PROTECTION_REPORT {}", json.replace("\n", ""));
        String path = System.getenv("SG_PROTECTION_REPORT");
        if (path != null && !path.isBlank()) {
            try {
                Files.writeString(Path.of(path), json);
            } catch (IOException e) {
                LOGGER.error("SG_PROTECTION could not write report", e);
            }
        }
    }
}

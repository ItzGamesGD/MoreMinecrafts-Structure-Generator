package dev.itzgamesgd.sgprotection.lab;

import dev.itzgamesgd.sgprotection.Guard;
import dev.itzgamesgd.sgprotection.GuardStats;
import dev.itzgamesgd.sgprotection.LabHooks;
import dev.itzgamesgd.sgprotection.MonsterRoomGeometry;
import dev.itzgamesgd.sgprotection.SgProtectionMod;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.WorldGenRegion;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.structure.BoundingBox;

/**
 * The validation lab mod (jar sg-worldgen-protection-lab, never shipped). Registered through the sg_worldgen_protection:lab entrypoint, it reads the
 * SG01_* lab settings, provides the instrumentation (read accounting, timing, sampler, decoration order, oracle) and the adversarial probes used by
 * the regression matrix. The production artifact contains none of this and reads none of these variables.
 */
public final class LabMod implements LabHooks {
    private final Config config = parse();
    private final List<String> zoneProbe = new ArrayList<>();
    private int zoneProbeRuns;
    private final java.util.concurrent.atomic.AtomicInteger avoidableMonster = new java.util.concurrent.atomic.AtomicInteger();
    private final java.util.concurrent.atomic.AtomicInteger avoidableGeode = new java.util.concurrent.atomic.AtomicInteger();

    private static String env(String name) {
        String v = System.getenv(name);
        return v == null || v.isBlank() ? null : v.trim();
    }

    private static <E extends Enum<E>> E enumOf(String name, Class<E> type, E fallback) {
        String v = env(name);
        if (v == null) return fallback;
        try {
            return Enum.valueOf(type, v.toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            throw new IllegalStateException("SG lab: unknown value '" + v + "' for " + name, e);
        }
    }

    private static Config parse() {
        String features = env("SG01_FEATURES");
        return new Config(enumOf("SG01_GUARD_MODE", Guard.Mode.class, Guard.Mode.ENFORCE), enumOf("SG01_REFINE", Guard.Refine.class, Guard.Refine.HYBRID),
                features == null ? "both" : features, enumOf("SG01_FIXTURE", Guard.Fixture.class, Guard.Fixture.NONE), enumOf("SG01_FAULT", Guard.Fault.class, Guard.Fault.NONE),
                "1".equals(env("SG01_SHADOW")), "monster_room".equalsIgnoreCase(env("SG01_ORACLE")));
    }

    @Override
    public Config config() {
        return config;
    }

    @Override
    public void enter() {
        Probe.enter();
    }

    @Override
    public void exit() {
        Probe.exit();
    }

    @Override
    public void mark() {
        Perf.mark();
    }

    @Override
    public void decisionDone(boolean geode) {
        if (geode) Perf.decisionDone(Perf.GEODE_DECISION_NS, null);
        else Perf.decisionDone(Perf.MONSTER_DECISION_NS, Perf.MONSTER_DECISION_BYTES);
    }

    @Override
    public void placeDone(boolean geode, boolean vanillaRan) {
        if (geode) Perf.placeDone(Perf.GEODE_PLACE_NS, vanillaRan ? Perf.GEODE_VANILLA_NS : null);
        else Perf.placeDone(Perf.MONSTER_PLACE_NS, vanillaRan ? Perf.MONSTER_VANILLA_NS : null);
    }

    @Override
    public void oracleBegin(GuardStats stats, WorldGenLevel level, BlockPos origin, List<BoundingBox> refined) {
        MonsterRoomOracle.begin(stats, level, origin, refined);
    }

    @Override
    public void oracleEnd(GuardStats stats, WorldGenLevel level, BlockPos origin) {
        MonsterRoomOracle.end(stats, level, origin);
    }

    /** Classifies a cancellation taken while not VERIFIED: avoidable if the VERIFIED decision (hybrid / configured geode box) would have allowed the attempt. */
    @Override
    public void unverifiedCancel(boolean geode, WorldGenLevel level, BlockPos origin, BoundingBox verifiedReach) {
        Probe.enter();
        try {
            boolean verifiedWouldCancel = geode ? Guard.collides(level, List.of(verifiedReach)) : Guard.collides(level, MonsterRoomGeometry.passingBoxes(level, origin));
            if (!verifiedWouldCancel) (geode ? avoidableGeode : avoidableMonster).incrementAndGet();
        } finally {
            Probe.exit();
        }
    }

    @Override
    public String fingerprintBreak() {
        return env("SG01_LAB_FINGERPRINT_BREAK");
    }

    /**
     * Adversarial test of the 3x3-chunk write-zone assumption. For the first three monster-room attempts it tries to place a marker block just inside
     * and just outside the write zone of the current region, reads the cell back, and restores it. The ZONE guard is only conservative if every
     * outside write is refused.
     */
    @Override
    public synchronized void zoneProbe(WorldGenLevel level, BlockPos origin) {
        if (zoneProbeRuns >= 3 || !(level instanceof WorldGenRegion region)) return;
        zoneProbeRuns++;
        int cx = region.getCenter().x();
        int cz = region.getCenter().z();
        int y = origin.getY();
        int[][] cells = {
                {(cx - 1) * 16, cz * 16 + 8, 1}, {(cx + 1) * 16 + 15, cz * 16 + 8, 1}, {cx * 16 + 8, (cz - 1) * 16, 1}, {cx * 16 + 8, (cz + 1) * 16 + 15, 1},
                {(cx - 1) * 16, (cz - 1) * 16, 1}, {(cx + 1) * 16 + 15, (cz + 1) * 16 + 15, 1},
                {(cx - 2) * 16 + 15, cz * 16 + 8, 0}, {(cx + 2) * 16, cz * 16 + 8, 0}, {cx * 16 + 8, (cz - 2) * 16 + 15, 0}, {cx * 16 + 8, (cz + 2) * 16, 0},
                {(cx - 2) * 16 + 15, (cz - 2) * 16 + 15, 0}, {(cx + 2) * 16, (cz + 2) * 16, 0}};
        for (int[] c : cells) {
            BlockPos pos = new BlockPos(c[0], y, c[1]);
            String result;
            try {
                BlockState before = level.getBlockState(pos);
                BlockState marker = before.is(Blocks.GOLD_BLOCK) ? Blocks.IRON_BLOCK.defaultBlockState() : Blocks.GOLD_BLOCK.defaultBlockState();
                boolean returned = level.setBlock(pos, marker, 2);
                boolean applied = level.getBlockState(pos) == marker;
                if (applied) level.setBlock(pos, before, 2);
                result = "setBlock=" + returned + " applied=" + applied;
                zoneProbe.add(String.format("{\"centre\":[%d,%d],\"cell\":[%d,%d],\"inside_zone\":%b,\"result\":\"%s\"}", cx, cz, c[0], c[1], c[2] == 1, result));
            } catch (RuntimeException e) {
                zoneProbe.add(String.format("{\"centre\":[%d,%d],\"cell\":[%d,%d],\"inside_zone\":%b,\"result\":\"exception %s\"}", cx, cz, c[0], c[1], c[2] == 1,
                        e.getClass().getSimpleName()));
            }
        }
    }

    @Override
    public synchronized String reportExtras() {
        return ",\"probe\":" + Probe.json() + ",\"perf\":" + Perf.json() + ",\"decoration_order\":" + Probe.decorationJson() + ",\"avoidable_unverified_cancels\":{\"monster_room\":" + avoidableMonster.get() + ",\"geode\":" + avoidableGeode.get() + "},\"zone_probe\":[" + String.join(",", zoneProbe) + "]";
    }

    @Override
    public void serverStarted(MinecraftServer server) {
        Sampler.start(server);
    }

    @Override
    public void serverStopping() {
        Sampler.stop();
    }
}

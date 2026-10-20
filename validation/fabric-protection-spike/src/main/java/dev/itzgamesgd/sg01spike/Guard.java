package dev.itzgamesgd.sg01spike;

import it.unimi.dsi.fastutil.longs.LongSet;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.WorldGenRegion;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructurePiece;
import net.minecraft.world.level.levelgen.structure.StructureStart;

/**
 * Feature-level collision guard. Reads only data that the FEATURES step already guarantees (references of the 3x3 write zone, starts within
 * ChunkStatus.MAX_STRUCTURE_DISTANCE). It never asks for a status the step does not provide, so it cannot schedule or wait for chunk generation.
 */
public final class Guard {
    public enum Mode { OBSERVE, ENFORCE }

    /** Test-only fault injection (SG01_FAULT): exercises the "structure data unavailable" paths on demand. */
    public enum Fault { NONE, OUT_OF_RANGE, STATUS_TOO_HIGH, MISSING_START, PRECHECK_BLIND }

    /**
     * Experiment-only fixture (SG01_FIXTURE), used only for causal attribution and never shipped. NO_GEODE cancels every geode placement
     * without any guard, so the remaining damage can be attributed to monster rooms alone.
     */
    public enum Fixture { NONE, NO_GEODE }

    /** Experiment-only refinement (SG01_REFINE). PRECHECK replicates vanilla's read-only precheck per room variant. OFF is the N7-A behaviour. */
    public enum Refine { OFF, PRECHECK, HYBRID }

    /**
     * Lab switch (SG01_LAB=1). Production runs with ENFORCE, the hybrid monster-room decision and no instrumentation. Every behaviour-changing
     * knob below (mode, fault injection, fixture, refinement, oracle, shadow check, per-hook selection) and the timing instrumentation exist only
     * for the validation lab: if one is set without SG01_LAB=1 the server refuses to start instead of silently running a non-production guard.
     */
    public static final boolean LAB = "1".equals(env("sg01.lab", "SG01_LAB"));

    public static final Mode MODE = parseEnum("sg01.guard.mode", "SG01_GUARD_MODE", Mode.class, Mode.ENFORCE, true);
    public static final Fault FAULT = parseEnum("sg01.fault", "SG01_FAULT", Fault.class, Fault.NONE, false);
    public static final Fixture FIXTURE = parseEnum("sg01.fixture", "SG01_FIXTURE", Fixture.class, Fixture.NONE, false);
    public static final Refine REFINE = parseEnum("sg01.refine", "SG01_REFINE", Refine.class, Refine.HYBRID, false);
    /** Lab-only oracle (SG01_ORACLE=monster_room): vanilla runs unguarded and the outcome is classified. Never cancels. */
    public static final boolean ORACLE_MONSTER_ROOM = "monster_room".equalsIgnoreCase(labEnv("sg01.oracle", "SG01_ORACLE"));
    /** Lab-only (SG01_SHADOW=1, HYBRID only): also checks that the broad phase never rejects an attempt the refined decision would cancel. */
    public static final boolean SHADOW = "1".equals(labEnv("sg01.shadow", "SG01_SHADOW"));
    public static final GuardStats GEODE = new GuardStats("geode");
    public static final GuardStats MONSTER_ROOM = new GuardStats("monster_room");

    /** Lab-only (SG01_FEATURES = geode | monster_room | both | none): enable the decision for one hook at a time to prove each hook independently. */
    private static final String FEATURES = labEnv("sg01.features", "SG01_FEATURES") == null ? "both" : labEnv("sg01.features", "SG01_FEATURES");

    private Guard() {
    }

    private static String env(String property, String variable) {
        String value = System.getProperty(property, System.getenv(variable));
        return value == null || value.isBlank() ? null : value.trim();
    }

    /** A lab-only setting: its mere presence without SG01_LAB=1 is a configuration error. */
    private static String labEnv(String property, String variable) {
        String value = env(property, variable);
        if (value != null && !LAB) {
            throw new IllegalStateException("SG protection: " + variable + "=" + value + " is a validation-lab setting and is refused in production."
                    + " Unset it (the production guard needs no configuration), or set SG01_LAB=1 for lab runs.");
        }
        return value;
    }

    private static <E extends Enum<E>> E parseEnum(String property, String variable, Class<E> type, E fallback, boolean guardModeNames) {
        String value = labEnv(property, variable);
        if (value == null) return fallback;
        if (guardModeNames && value.equalsIgnoreCase("enforce")) return Enum.valueOf(type, "ENFORCE");
        if (guardModeNames && value.equalsIgnoreCase("observe")) return Enum.valueOf(type, "OBSERVE");
        try {
            return Enum.valueOf(type, value.toUpperCase(Locale.ROOT));
        } catch (IllegalArgumentException e) {
            throw new IllegalStateException("SG protection spike: unknown value '" + value + "' for " + variable + " (" + type.getSimpleName() + ")", e);
        }
    }

    private static boolean enabled(String feature) {
        return FEATURES.equals("both") || FEATURES.equals(feature);
    }

    /** @return true if the feature instance must be cancelled (always false in OBSERVE mode, where the decision is only recorded). */
    public static boolean shouldCancel(GuardStats stats, WorldGenLevel level, BlockPos origin, BoundingBox reach) {
        return shouldCancel(stats, level, origin, List.of(reach));
    }

    /**
     * @param reaches every box the feature could write into; an empty list means vanilla writes nothing, so there is nothing to decide.
     * @return true if the feature instance must be cancelled (never true in OBSERVE mode).
     */
    public static boolean shouldCancel(GuardStats stats, WorldGenLevel level, BlockPos origin, List<BoundingBox> reaches) {
        stats.attempts.incrementAndGet();
        if (reaches.isEmpty()) {
            stats.noWrite.incrementAndGet();
            return false;
        }
        if (!enabled(stats.feature)) return false;
        if (!(level instanceof WorldGenRegion region)) {
            stats.notWorldgen.incrementAndGet();
            return false;
        }
        Probe.enter();
        try {
            return decide(stats, region, origin, reaches);
        } finally {
            Probe.exit();
        }
    }

    /**
     * HYBRID decision (N7-A3). The broad phase is the N7-A reach: if no protected piece intersects it, no variant of the refined reach can
     * intersect one either (every refined reach is a subset of it), so the narrow precheck is skipped. Otherwise the refined decision is taken.
     * Decisions are identical to PRECHECK; this is checked by SHADOW.
     */
    public static boolean shouldCancelHybrid(GuardStats stats, WorldGenLevel level, BlockPos origin, BoundingBox broad,
                                             java.util.function.Supplier<List<BoundingBox>> narrow) {
        stats.attempts.incrementAndGet();
        if (!enabled(stats.feature)) return false;
        if (!(level instanceof WorldGenRegion region)) {
            stats.notWorldgen.incrementAndGet();
            return false;
        }
        Probe.enter();
        try {
            boolean broadHit = scan(region, List.of(broad), false).verdict != null;
            if (!broadHit) {
                stats.hybridSkip.incrementAndGet();
                if (SHADOW) {
                    stats.shadowChecks.incrementAndGet();
                    if (collides(level, narrow.get())) stats.shadowViolations.incrementAndGet();
                }
                return false;
            }
            List<BoundingBox> reaches = narrow.get();
            if (reaches.isEmpty()) {
                stats.noWrite.incrementAndGet();
                nearMiss(region, broad, stats);
                return false;
            }
            boolean cancel = decide(stats, region, origin, reaches);
            if (!cancel) nearMiss(region, broad, stats);
            return cancel;
        } finally {
            Probe.exit();
        }
    }

    /** The hybrid decision allows vanilla although a protected piece overlaps the widest footprint: arm the monster-room self-check watch. */
    private static void nearMiss(WorldGenRegion region, BoundingBox broad, GuardStats stats) {
        if (!stats.feature.equals("monster_room")) return;
        List<BoundingBox> pieces = pieceBoxes(region, broad);
        if (pieces != null && !pieces.isEmpty()) MonsterRoomSelfCheck.begin(region, broad, pieces);
    }

    /** Side-effect-free decision for the oracle: true if the reaches intersect a protected piece or the structure data is unavailable. */
    public static boolean collides(WorldGenLevel level, List<BoundingBox> reaches) {
        if (reaches.isEmpty() || !(level instanceof WorldGenRegion region)) return false;
        Probe.enter();
        try {
            return scan(region, reaches, false).verdict != null;
        } finally {
            Probe.exit();
        }
    }

    /** Protected piece boxes intersecting {@code box} (for the oracle). Returns null if the structure data is unavailable. */
    static List<BoundingBox> pieceBoxes(WorldGenRegion region, BoundingBox box) {
        Finding f = scan(region, List.of(box), true);
        return "unavailable".equals(f.verdict) ? null : f.hits;
    }

    private static boolean decide(GuardStats stats, WorldGenRegion region, BlockPos origin, List<BoundingBox> reaches) {
        Finding f = scan(region, reaches, false);
        ChunkPos centre = region.getCenter();
        if (f.verdict == null) {
            if (f.sawReference) stats.clear.incrementAndGet();
            else stats.fastPath.incrementAndGet();
            return false;
        }
        if (f.verdict.equals("collision")) stats.collisions.incrementAndGet();
        else stats.unavailable.incrementAndGet();
        stats.event(String.format("%s origin=%d,%d,%d centre=%d,%d reaches=%s -> %s (%s)%s", stats.feature, origin.getX(), origin.getY(), origin.getZ(),
                centre.x(), centre.z(), reaches, f.verdict, f.detail, MODE == Mode.ENFORCE ? " CANCELLED" : " observed"));
        if (f.verdict.equals("unavailable")) {
            SpikeMod.LOGGER.warn("SG_SPIKE unavailable structure data for {} at {}: {} (instance {})", stats.feature, origin, f.detail,
                    MODE == Mode.ENFORCE ? "cancelled" : "observed only");
        }
        if (MODE == Mode.ENFORCE) {
            stats.cancelled.incrementAndGet();
            return true;
        }
        stats.wouldCancel.incrementAndGet();
        return false;
    }

    private record Finding(String verdict, String detail, List<BoundingBox> hits, boolean sawReference) {
    }

    /**
     * Walks the references of the chunks overlapped by the reach boxes and checks every referenced start's pieces.
     * With {@code collectAll} false it stops at the first collision; with true it returns every piece box that intersects a reach.
     */
    private static Finding scan(WorldGenRegion region, List<BoundingBox> reaches, boolean collectAll) {
        int minX = Integer.MAX_VALUE;
        int maxX = Integer.MIN_VALUE;
        int minZ = Integer.MAX_VALUE;
        int maxZ = Integer.MIN_VALUE;
        for (BoundingBox r : reaches) {
            minX = Math.min(minX, r.minX());
            maxX = Math.max(maxX, r.maxX());
            minZ = Math.min(minZ, r.minZ());
            maxZ = Math.max(maxZ, r.maxZ());
        }
        Set<Structure> protectedSet = ProtectionConfig.protectedStructures();
        ChunkPos centre = region.getCenter();
        Set<Long> seenStarts = new HashSet<>();
        List<BoundingBox> hits = new ArrayList<>();
        boolean sawReference = false;
        int minCx = Math.max(minX >> 4, centre.x() - 1);
        int maxCx = Math.min(maxX >> 4, centre.x() + 1);
        int minCz = Math.max(minZ >> 4, centre.z() - 1);
        int maxCz = Math.min(maxZ >> 4, centre.z() + 1);
        for (int cx = minCx; cx <= maxCx; cx++) {
            for (int cz = minCz; cz <= maxCz; cz++) {
                if (!region.hasChunk(cx, cz)) {
                    return new Finding("unavailable", "chunk " + cx + "," + cz + " outside the step's cache", hits, sawReference);
                }
                ChunkAccess chunk;
                Map<Structure, LongSet> references;
                try {
                    chunk = region.getChunk(cx, cz, ChunkStatus.STRUCTURE_REFERENCES);
                    references = chunk.getAllReferences();
                } catch (RuntimeException e) {
                    return new Finding("unavailable", "references of chunk " + cx + "," + cz + ": " + e.getClass().getSimpleName(), hits, sawReference);
                }
                for (Map.Entry<Structure, LongSet> entry : references.entrySet()) {
                    if (!protectedSet.contains(entry.getKey())) continue;
                    sawReference = true;
                    if (FAULT == Fault.OUT_OF_RANGE && !region.hasChunk(centre.x() + 9, centre.z())) {
                        return new Finding("unavailable", "[fault-injection] chunk at distance 9 is outside the step's chunk cache (hasChunk=false)", hits, sawReference);
                    }
                    if (FAULT == Fault.STATUS_TOO_HIGH) {
                        try {
                            region.getChunk(centre.x() + 2, centre.z(), ChunkStatus.STRUCTURE_REFERENCES);
                        } catch (RuntimeException e) {
                            return new Finding("unavailable", "[fault-injection] getChunk(distance 2, STRUCTURE_REFERENCES) threw " + e.getClass().getSimpleName()
                                    + " instead of generating", hits, sawReference);
                        }
                    }
                    for (long key : entry.getValue()) {
                        if (!seenStarts.add(key)) continue;
                        ChunkPos startPos = ChunkPos.unpack(key);
                        if (centre.getChessboardDistance(startPos) > ChunkStatus.MAX_STRUCTURE_DISTANCE || !region.hasChunk(startPos.x(), startPos.z())) {
                            return new Finding("unavailable", "start chunk " + startPos.x() + "," + startPos.z() + " beyond readable distance", hits, sawReference);
                        }
                        StructureStart start;
                        try {
                            start = region.getChunk(startPos.x(), startPos.z(), ChunkStatus.STRUCTURE_STARTS).getStartForStructure(entry.getKey());
                        } catch (RuntimeException e) {
                            return new Finding("unavailable", "start chunk " + startPos.x() + "," + startPos.z() + ": " + e.getClass().getSimpleName(), hits, sawReference);
                        }
                        if (FAULT == Fault.MISSING_START) start = null;
                        if (start == null || !start.isValid()) {
                            String detail = (FAULT == Fault.MISSING_START ? "[fault-injection] " : "") + "referenced start at " + startPos.x() + "," + startPos.z()
                                    + " is " + (start == null ? "missing" : "invalid");
                            return new Finding("unavailable", detail, hits, sawReference);
                        }
                        int index = 0;
                        for (StructurePiece piece : start.getPieces()) {
                            BoundingBox box = piece.getBoundingBox();
                            for (BoundingBox reach : reaches) {
                                if (!box.intersects(reach)) continue;
                                String detail = "start " + startPos.x() + "," + startPos.z() + " piece #" + index + " " + box;
                                if (!collectAll) return new Finding("collision", detail, hits, sawReference);
                                hits.add(box);
                                break;
                            }
                            index++;
                        }
                    }
                }
            }
        }
        return new Finding(hits.isEmpty() ? null : "collision", hits.isEmpty() ? "" : "piece boxes intersecting the box", hits, sawReference);
    }
}

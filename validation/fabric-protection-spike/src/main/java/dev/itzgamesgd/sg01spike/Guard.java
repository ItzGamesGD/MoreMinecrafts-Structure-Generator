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
    public enum Fault { NONE, OUT_OF_RANGE, STATUS_TOO_HIGH, MISSING_START }

    /**
     * Experiment-only fixture (SG01_FIXTURE), used only for causal attribution and never shipped. NO_GEODE cancels every geode placement
     * without any guard, so the remaining damage can be attributed to monster rooms alone.
     */
    public enum Fixture { NONE, NO_GEODE }

    /** Experiment-only refinement (SG01_REFINE). PRECHECK replicates vanilla's read-only precheck per room variant. OFF is the N7-A behaviour. */
    public enum Refine { OFF, PRECHECK }

    public static final Mode MODE = parseEnum("sg01.guard.mode", "SG01_GUARD_MODE", Mode.class, Mode.ENFORCE, true);
    public static final Fault FAULT = parseEnum("sg01.fault", "SG01_FAULT", Fault.class, Fault.NONE, false);
    public static final Fixture FIXTURE = parseEnum("sg01.fixture", "SG01_FIXTURE", Fixture.class, Fixture.NONE, false);
    public static final Refine REFINE = parseEnum("sg01.refine", "SG01_REFINE", Refine.class, Refine.OFF, false);
    /** Experiment-only oracle (SG01_ORACLE=monster_room): vanilla runs unguarded and the outcome is classified. Never cancels. */
    public static final boolean ORACLE_MONSTER_ROOM = "monster_room".equalsIgnoreCase(env("sg01.oracle", "SG01_ORACLE"));
    public static final GuardStats GEODE = new GuardStats("geode");
    public static final GuardStats MONSTER_ROOM = new GuardStats("monster_room");

    /** Test-only (SG01_FEATURES = geode | monster_room | both | none): enable the decision for one hook at a time to prove each hook independently. */
    private static final String FEATURES = env("sg01.features", "SG01_FEATURES") == null ? "both" : env("sg01.features", "SG01_FEATURES");

    private Guard() {
    }

    private static String env(String property, String variable) {
        String value = System.getProperty(property, System.getenv(variable));
        return value == null || value.isBlank() ? null : value.trim();
    }

    private static <E extends Enum<E>> E parseEnum(String property, String variable, Class<E> type, E fallback, boolean guardModeNames) {
        String value = env(property, variable);
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

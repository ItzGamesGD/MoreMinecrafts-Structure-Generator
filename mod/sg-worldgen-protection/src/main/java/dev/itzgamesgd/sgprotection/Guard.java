package dev.itzgamesgd.sgprotection;

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

    /** Lab fault injection (selected by the lab mod, never by production): exercises the "structure data unavailable" paths on demand. */
    public enum Fault { NONE, OUT_OF_RANGE, STATUS_TOO_HIGH, MISSING_START, PRECHECK_BLIND, GEODE_SHRUNK, ZONE_PROBE, PRECHECK_BLIND_NEAR, BOX_SHRUNK }

    /**
     * Experiment-only fixture (lab only), used only for causal attribution and never shipped. NO_GEODE cancels every geode placement
     * without any guard, so the remaining damage can be attributed to monster rooms alone.
     */
    public enum Fixture { NONE, NO_GEODE }

    /**
     * Monster-room decision. OFF = the box guard (N7-A reach: union of all variant footprints) and the production decision since N7-E; PRECHECK/HYBRID use the
     * replicated read-only precheck and exist for the validation lab only (N7-D showed a replica fault confined to near-miss geometry can pass calibration and
     * damage a protected piece before it is detected); ZONE = the whole write zone, used when a drift is detected.
     */
    public enum Refine { OFF, PRECHECK, HYBRID, ZONE }

    /** Configuration in force: the production defaults unless the validation lab installed hooks (see {@link LabHooks}). */
    public static LabHooks.Config cfg() {
        return LabHooks.get().config();
    }

    public static final GuardStats GEODE = new GuardStats("geode");
    public static final GuardStats MONSTER_ROOM = new GuardStats("monster_room");

    private Guard() {
    }

    private static boolean enabled(String feature) {
        return hookActive(feature);
    }

    /**
     * The feature-level hook for {@code feature} is active: selected by the lab, or forced because the drift guard demoted it to ZONE (vanilla classes
     * the write-level guard depends on did not match the validated ones, so the second, independent layer is switched on). Otherwise the write-level guard
     * alone protects the pieces and the feature runs untouched.
     */
    public static boolean hookActive(String feature) {
        String f = cfg().features();
        if (f.equals("both") || f.equals(feature)) return true;
        DriftGuard.State state = feature.equals("geode") ? DriftGuard.GEODE : DriftGuard.MONSTER_ROOM;
        return state.level() == DriftGuard.Level.ZONE;
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
        LabHooks.get().enter();
        try {
            return decide(stats, region, origin, reaches);
        } finally {
            LabHooks.get().exit();
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
        LabHooks.get().enter();
        try {
            boolean broadHit = scan(region, List.of(broad), false, null).verdict != null;
            if (!broadHit) {
                stats.hybridSkip.incrementAndGet();
                if (cfg().shadow()) {
                    stats.shadowChecks.incrementAndGet();
                    if (collides(level, narrow.get())) stats.shadowViolations.incrementAndGet();
                }
                return false;
            }
            List<BoundingBox> reaches = narrow.get();
            if (reaches.isEmpty()) {
                stats.noWrite.incrementAndGet();
                nearMiss(region, broad, reaches);
                return false;
            }
            boolean cancel = decide(stats, region, origin, reaches);
            if (!cancel) nearMiss(region, broad, reaches);
            return cancel;
        } finally {
            LabHooks.get().exit();
        }
    }

    /** The hybrid decision allows vanilla although a protected piece overlaps the widest footprint: verify what vanilla does there (after the fact). */
    private static void nearMiss(WorldGenRegion region, BoundingBox broad, List<BoundingBox> predicted) {
        List<BoundingBox> pieces = pieceBoxes(region, broad);
        if (pieces == null || pieces.isEmpty()) return;
        DriftGuard.MONSTER_ROOM.nearMisses.incrementAndGet();
        DriftGuard.arm(DriftGuard.MONSTER_ROOM, region, inflate(broad, 2), predicted, broad);
    }

    public static BoundingBox inflate(BoundingBox b, int n) {
        return new BoundingBox(b.minX() - n, b.minY() - n, b.minZ() - n, b.maxX() + n, b.maxY() + n, b.maxZ() + n);
    }

    /** True if a protected piece intersects {@code box} (false if none, or outside world generation). */
    public static boolean piecesNear(WorldGenLevel level, BoundingBox box) {
        if (!(level instanceof WorldGenRegion region)) return false;
        LabHooks.get().enter();
        try {
            List<BoundingBox> pieces = pieceBoxes(region, box);
            return pieces != null && !pieces.isEmpty();
        } finally {
            LabHooks.get().exit();
        }
    }

    /** Side-effect-free decision for the oracle: true if the reaches intersect a protected piece or the structure data is unavailable. */
    public static boolean collides(WorldGenLevel level, List<BoundingBox> reaches) {
        if (reaches.isEmpty() || !(level instanceof WorldGenRegion region)) return false;
        LabHooks.get().enter();
        try {
            return scan(region, reaches, false, null).verdict != null;
        } finally {
            LabHooks.get().exit();
        }
    }

    /** Protected piece boxes intersecting {@code box} (for the oracle). Returns null if the structure data is unavailable. */
    public static List<BoundingBox> pieceBoxes(WorldGenRegion region, BoundingBox box) {
        Finding f = scan(region, List.of(box), true, null);
        return "unavailable".equals(f.verdict) ? null : f.hits;
    }

    /** Collects what a write-zone scan could not establish (N10-R): footprints in chunk coordinates and the causes, counted by name. */
    public static final class Uncertainty {
        public final List<int[]> rects = new ArrayList<>();
        public final java.util.Map<String, Integer> causes = new java.util.LinkedHashMap<>();
        final int[] zone;

        public Uncertainty(int[] zone) {
            this.zone = zone;
        }

        void add(String cause, int[] rect) {
            causes.merge(cause, 1, Integer::sum);
            if (rect != null) rects.add(rect);
        }
    }

    /**
     * Write-zone scan: every protected piece box intersecting {@code zoneBox}, <em>including those found before or around unreadable data</em>, plus the
     * bounded footprint (never larger than the 3x3 write zone) of whatever could not be read. Reads only chunks already in the region's cache.
     */
    public static List<BoundingBox> scanZone(WorldGenRegion region, BoundingBox zoneBox, Uncertainty uncertain) {
        return scan(region, List.of(zoneBox), true, uncertain).hits;
    }

    private static boolean decide(GuardStats stats, WorldGenRegion region, BlockPos origin, List<BoundingBox> reaches) {
        Finding f = scan(region, reaches, false, null);
        ChunkPos centre = region.getCenter();
        if (f.verdict == null) {
            if (f.sawReference) stats.clear.incrementAndGet();
            else stats.fastPath.incrementAndGet();
            return false;
        }
        if (f.verdict.equals("collision")) stats.collisions.incrementAndGet();
        else stats.unavailable.incrementAndGet();
        stats.event(String.format("%s origin=%d,%d,%d centre=%d,%d reaches=%s -> %s (%s)%s", stats.feature, origin.getX(), origin.getY(), origin.getZ(),
                centre.x(), centre.z(), reaches, f.verdict, f.detail, cfg().mode() == Mode.ENFORCE ? " CANCELLED" : " observed"));
        if (f.verdict.equals("unavailable")) {
            SgProtectionMod.LOGGER.warn("SG_PROTECTION unavailable structure data for {} at {}: {} (instance {})", stats.feature, origin, f.detail,
                    cfg().mode() == Mode.ENFORCE ? "cancelled" : "observed only");
        }
        if (cfg().mode() == Mode.ENFORCE) {
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
    private static Finding scan(WorldGenRegion region, List<BoundingBox> reaches, boolean collectAll, Uncertainty u) {
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
                    if (u == null) return new Finding("unavailable", "chunk " + cx + "," + cz + " outside the step's cache", hits, sawReference);
                    u.add("chunk_missing", UncertainFootprint.ofChunk(cx, cz, u.zone));
                    continue;
                }
                ChunkAccess chunk;
                Map<Structure, LongSet> references;
                try {
                    chunk = region.getChunk(cx, cz, ChunkStatus.STRUCTURE_REFERENCES);
                    references = chunk.getAllReferences();
                } catch (RuntimeException e) {
                    if (u == null) return new Finding("unavailable", "references of chunk " + cx + "," + cz + ": " + e.getClass().getSimpleName(), hits, sawReference);
                    u.add("references_failed", UncertainFootprint.ofChunk(cx, cz, u.zone));
                    continue;
                }
                for (Map.Entry<Structure, LongSet> entry : references.entrySet()) {
                    if (!protectedSet.contains(entry.getKey())) continue;
                    sawReference = true;
                    if (cfg().fault() == Fault.OUT_OF_RANGE && !region.hasChunk(centre.x() + 9, centre.z())) {
                        if (u == null) return new Finding("unavailable", "[fault-injection] chunk at distance 9 is outside the step's chunk cache (hasChunk=false)", hits, sawReference);
                        for (long key : entry.getValue()) u.add("start_out_of_range", UncertainFootprint.ofStart(ChunkPos.unpack(key).x(), ChunkPos.unpack(key).z(), u.zone));
                        continue;
                    }
                    if (cfg().fault() == Fault.STATUS_TOO_HIGH) {
                        // Simulated failed read of a start chunk. It deliberately makes no engine call: a real getChunk() for a chunk beyond the cache can block on a
                        // worker that is itself running this code (found on a one-worker CI runner, N10-R), which would be a test-only deadlock.
                        if (u == null) return new Finding("unavailable", "[fault-injection] simulated failed read of a start chunk", hits, sawReference);
                        for (long key : entry.getValue()) u.add("start_failed", UncertainFootprint.ofStart(ChunkPos.unpack(key).x(), ChunkPos.unpack(key).z(), u.zone));
                        continue;
                    }
                    for (long key : entry.getValue()) {
                        if (!seenStarts.add(key)) continue;
                        ChunkPos startPos = ChunkPos.unpack(key);
                        if (centre.getChessboardDistance(startPos) > ChunkStatus.MAX_STRUCTURE_DISTANCE || !region.hasChunk(startPos.x(), startPos.z())) {
                            if (u == null) return new Finding("unavailable", "start chunk " + startPos.x() + "," + startPos.z() + " beyond readable distance", hits, sawReference);
                            u.add("start_out_of_range", UncertainFootprint.ofStart(startPos.x(), startPos.z(), u.zone));
                            continue;
                        }
                        StructureStart start;
                        try {
                            start = region.getChunk(startPos.x(), startPos.z(), ChunkStatus.STRUCTURE_STARTS).getStartForStructure(entry.getKey());
                        } catch (RuntimeException e) {
                            if (u == null) return new Finding("unavailable", "start chunk " + startPos.x() + "," + startPos.z() + ": " + e.getClass().getSimpleName(), hits, sawReference);
                            u.add("start_failed", UncertainFootprint.ofStart(startPos.x(), startPos.z(), u.zone));
                            continue;
                        }
                        if (cfg().fault() == Fault.MISSING_START) start = null;
                        if (start == null || !start.isValid()) {
                            String detail = (cfg().fault() == Fault.MISSING_START ? "[fault-injection] " : "") + "referenced start at " + startPos.x() + "," + startPos.z()
                                    + " is " + (start == null ? "missing" : "invalid");
                            if (u == null) return new Finding("unavailable", detail, hits, sawReference);
                            u.add("start_missing_or_invalid", UncertainFootprint.ofStart(startPos.x(), startPos.z(), u.zone));
                            continue;
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

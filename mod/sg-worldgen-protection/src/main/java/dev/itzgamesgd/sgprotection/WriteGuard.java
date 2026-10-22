package dev.itzgamesgd.sgprotection;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.WorldGenRegion;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.Structure;

/**
 * Write-level protection (N8-R). While chunks are generated, every block written through {@code WorldGenRegion.setBlock} is checked against the
 * piece boxes of the protected structures that intersect the region's 3x3-chunk write zone; a write into such a box is refused unless the protected
 * structure itself is being placed. This closes the gap the N8 audit found in the feature-level guard: the feature hooks only knew geodes and monster
 * rooms, while sculk patches, sulfur and speleothem features, lakes, clay patches and other structures overwrote pieces too (24 of 270 sites).
 *
 * The check is read-only and cheap: the list of piece boxes is computed once per region (a handful of reference lookups) and is empty for almost every
 * region, in which case a write costs one field read. It never requests or generates a chunk (the same reads as {@link Guard}).
 */
public final class WriteGuard {
    public static final AtomicLong REGIONS = new AtomicLong();
    public static final AtomicLong REGIONS_WITH_PIECES = new AtomicLong();
    /** Regions in which some structure data could not be read (each incident is also counted by cause). */
    public static final AtomicLong UNAVAILABLE = new AtomicLong();
    public static final AtomicLong BLOCKED = new AtomicLong();
    /** Writes refused because they fall in the bounded footprint of unreadable structure data (fail-closed policy, N10-R). */
    public static final AtomicLong UNCERTAIN_REFUSED = new AtomicLong();
    private static final ConcurrentHashMap<String, AtomicLong> CAUSES = new ConcurrentHashMap<>();
    private static final List<String> EVENTS = new ArrayList<>();

    /** Number of unavailable-data incidents that are logged individually; later ones are logged every {@link #LOG_EVERY}th time (counters stay exact). */
    private static final int LOG_FIRST = 10;
    private static final int LOG_EVERY = 100;

    /**
     * What protection knows about one region's write zone: the protected piece boxes found (also those found next to unreadable data), and the bounded
     * footprint (chunk rectangles, never larger than the 3x3 zone) in which protection could not be established. Immutable; cached per region instance.
     */
    public record Zone(List<BoundingBox> boxes, List<int[]> uncertain) {
        static final Zone EMPTY = new Zone(List.of(), List.of());

        public boolean isEmpty() {
            return boxes.isEmpty() && uncertain.isEmpty();
        }
    }

    private WriteGuard() {
    }

    public static boolean enabled() {
        return LabHooks.get().config().writeGuard();
    }

    /**
     * Policy for unavailable structure data (N10-R): never fall back to "unprotected". Boxes already found are kept and enforced; the area that could not
     * be established (the unreadable chunk column, or the part of the zone within the vanilla piece distance of an unreadable start) is refused for writes
     * that are not the structure's own. The effect of one incident is bounded by the nine chunk columns of the zone, it is counted by cause, and it is logged.
     * Only chunks already in the region's cache are read, nothing is requested or generated, and the result is computed once per region instance.
     */
    public static Zone zoneFor(WorldGenRegion region) {
        REGIONS.incrementAndGet();
        BoundingBox zoneBox = DriftGuard.zone(region);
        if (zoneBox == null) return Zone.EMPTY;
        ChunkPos centre = region.getCenter();
        Guard.Uncertainty u = new Guard.Uncertainty(UncertainFootprint.zone(centre.x(), centre.z()));
        List<BoundingBox> hits = Guard.scanZone(region, zoneBox, u);
        if (!hits.isEmpty()) REGIONS_WITH_PIECES.incrementAndGet();
        if (!u.causes.isEmpty()) {
            long n = UNAVAILABLE.incrementAndGet();
            u.causes.forEach((cause, times) -> CAUSES.computeIfAbsent(cause, k -> new AtomicLong()).addAndGet(times));
            if (n <= LOG_FIRST || n % LOG_EVERY == 0) {
                SgProtectionMod.LOGGER.error("SG_PROTECTION write guard: structure data unavailable in region {} (incident {}, causes {}); writes in chunk columns {} are refused, "
                        + "known piece boxes stay protected", centre, n, u.causes, u.rects.stream().map(java.util.Arrays::toString).toList());
            }
        }
        if (hits.isEmpty() && u.rects.isEmpty()) return Zone.EMPTY;
        return new Zone(List.copyOf(hits), List.copyOf(u.rects));
    }

    public static boolean blocked(Zone zone, BlockPos pos) {
        if (ExemptionScope.active()) return false;
        for (BoundingBox box : zone.boxes()) {
            if (box.isInside(pos)) {
                long n = BLOCKED.incrementAndGet();
                if (n <= 200) {
                    synchronized (EVENTS) {
                        EVENTS.add(pos.getX() + "," + pos.getY() + "," + pos.getZ());
                    }
                }
                return true;
            }
        }
        for (int[] rect : zone.uncertain()) {
            if (UncertainFootprint.contains(rect, pos.getX(), pos.getZ())) {
                UNCERTAIN_REFUSED.incrementAndGet();
                return true;
            }
        }
        return false;
    }

    /** The start being placed belongs to a protected structure: its own writes are allowed. Returns the token to pass to {@link #exitPlacement}. */
    public static boolean enterPlacement(Structure structure) {
        boolean own;
        try {
            own = ProtectionConfig.protectedStructures().contains(structure);
        } catch (IllegalStateException e) {
            own = false;
        }
        return ExemptionScope.enter(own);
    }

    /** Closes the scope opened by {@link #enterPlacement}; the decision taken on entry is carried by the token, so a reload in between cannot unbalance it. */
    public static void exitPlacement(boolean token) {
        ExemptionScope.exit(token);
    }

    public static String json() {
        String first;
        synchronized (EVENTS) {
            first = String.join(",", EVENTS.stream().limit(20).map(e -> "\"" + e + "\"").toList());
        }
        String causes = String.join(",", new java.util.TreeMap<>(CAUSES).entrySet().stream().map(e -> "\"" + e.getKey() + "\":" + e.getValue().get()).toList());
        return String.format("{\"enabled\":%b,\"regions\":%d,\"regions_with_pieces\":%d,\"unavailable\":%d,\"unavailable_causes\":{%s},\"uncertain_refused_writes\":%d,"
                + "\"blocked_writes\":%d,\"first_blocked\":[%s]}", enabled(), REGIONS.get(), REGIONS_WITH_PIECES.get(), UNAVAILABLE.get(), causes, UNCERTAIN_REFUSED.get(),
                BLOCKED.get(), first);
    }
}

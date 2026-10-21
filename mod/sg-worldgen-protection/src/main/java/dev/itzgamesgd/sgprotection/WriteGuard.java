package dev.itzgamesgd.sgprotection;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.WorldGenRegion;
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
    private static final ThreadLocal<int[]> OWN_PLACEMENT = ThreadLocal.withInitial(() -> new int[1]);
    public static final AtomicLong REGIONS = new AtomicLong();
    public static final AtomicLong REGIONS_WITH_PIECES = new AtomicLong();
    public static final AtomicLong UNAVAILABLE = new AtomicLong();
    public static final AtomicLong BLOCKED = new AtomicLong();
    private static final AtomicBoolean UNAVAILABLE_LOGGED = new AtomicBoolean();
    private static final List<String> EVENTS = new ArrayList<>();

    private WriteGuard() {
    }

    public static boolean enabled() {
        return LabHooks.get().config().writeGuard();
    }

    /** Piece boxes of the protected structures in the region's write zone; empty if none (or if the data is unavailable, which is counted and logged). */
    public static List<BoundingBox> boxesFor(WorldGenRegion region) {
        REGIONS.incrementAndGet();
        BoundingBox zone = DriftGuard.zone(region);
        List<BoundingBox> hits = zone == null ? List.of() : Guard.pieceBoxes(region, zone);
        if (hits == null) {
            UNAVAILABLE.incrementAndGet();
            if (UNAVAILABLE_LOGGED.compareAndSet(false, true)) {
                SgProtectionMod.LOGGER.error("SG_PROTECTION write guard: structure data was unavailable for region {}; writes in it are NOT checked (counted in the report)", region.getCenter());
            }
            return List.of();
        }
        if (!hits.isEmpty()) REGIONS_WITH_PIECES.incrementAndGet();
        return hits;
    }

    /** True if {@code pos} lies in a protected piece box and the protected structure is not the one writing. */
    public static boolean blocked(List<BoundingBox> boxes, BlockPos pos) {
        if (OWN_PLACEMENT.get()[0] > 0) return false;
        for (BoundingBox box : boxes) {
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
        return false;
    }

    /** The start being placed belongs to a protected structure: its own writes are allowed. */
    public static void enterPlacement(Structure structure) {
        boolean own;
        try {
            own = ProtectionConfig.protectedStructures().contains(structure);
        } catch (IllegalStateException e) {
            own = false;
        }
        if (own) OWN_PLACEMENT.get()[0]++;
    }

    public static void exitPlacement(Structure structure) {
        int[] depth = OWN_PLACEMENT.get();
        boolean own;
        try {
            own = ProtectionConfig.protectedStructures().contains(structure);
        } catch (IllegalStateException e) {
            own = false;
        }
        if (own && depth[0] > 0) depth[0]--;
    }

    public static synchronized String json() {
        return String.format("{\"enabled\":%b,\"regions\":%d,\"regions_with_pieces\":%d,\"unavailable\":%d,\"blocked_writes\":%d,\"first_blocked\":[%s]}", enabled(), REGIONS.get(),
                REGIONS_WITH_PIECES.get(), UNAVAILABLE.get(), BLOCKED.get(), String.join(",", EVENTS.stream().limit(20).map(e -> "\"" + e + "\"").toList()));
    }
}

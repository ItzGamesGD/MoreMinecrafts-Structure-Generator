package dev.itzgamesgd.sg01spike;

import java.util.ArrayList;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.levelgen.structure.BoundingBox;

/**
 * Vanilla MonsterRoomFeature.place (26.3) reads its footprint before it writes anything. Its size is drawn from the RandomSource as
 * xr, zr in {2, 3}; the write footprint of one variant is x in [-xr-1, xr+1], y in [-1, 4], z in [-zr-1, zr+1]. Vanilla writes nothing
 * when its precheck fails, so a variant whose precheck fails cannot touch any cell. The precheck below repeats vanilla's reads in the
 * same order with the same predicates. It only reads, and it reads the same cells vanilla would read, all inside the 3x3 chunk zone.
 */
public final class MonsterRoomGeometry {
    private static final int[] VARIANTS = {2, 3};

    private MonsterRoomGeometry() {
    }

    /** The N7-A reach: the union of every variant's footprint. */
    public static BoundingBox maxBox(BlockPos origin) {
        return box(origin, 3, 3);
    }

    static BoundingBox box(BlockPos origin, int xr, int zr) {
        return new BoundingBox(origin.getX() - xr - 1, origin.getY() - 1, origin.getZ() - zr - 1,
                origin.getX() + xr + 1, origin.getY() + 4, origin.getZ() + zr + 1);
    }

    /** Footprints of the variants whose vanilla precheck passes (only these can write). Empty means vanilla writes nothing. */
    public static List<BoundingBox> passingBoxes(WorldGenLevel level, BlockPos origin) {
        List<BoundingBox> out = new ArrayList<>(4);
        // Lab fault injection: simulates a vanilla change that makes the replicated precheck under-estimate the footprint (exercises the runtime watch).
        if (Guard.FAULT == Guard.Fault.PRECHECK_BLIND) return out;
        for (int xr : VARIANTS) {
            for (int zr : VARIANTS) {
                if (precheck(level, origin, xr, zr)) out.add(box(origin, xr, zr));
            }
        }
        return out;
    }

    /** Mirror of the first loop of MonsterRoomFeature.place (reads only). */
    static boolean precheck(WorldGenLevel level, BlockPos origin, int xr, int zr) {
        int minX = -xr - 1;
        int maxX = xr + 1;
        int minZ = -zr - 1;
        int maxZ = zr + 1;
        int holeCount = 0;
        for (int dx = minX; dx <= maxX; dx++) {
            for (int dy = -1; dy <= 4; dy++) {
                for (int dz = minZ; dz <= maxZ; dz++) {
                    BlockPos holePos = origin.offset(dx, dy, dz);
                    boolean solid = level.getBlockState(holePos).isSolid();
                    if (dy == -1 && !solid) return false;
                    if (dy == 4 && !solid) return false;
                    if ((dx == minX || dx == maxX || dz == minZ || dz == maxZ) && dy == 0 && level.isEmptyBlock(holePos) && level.isEmptyBlock(holePos.above())) {
                        holeCount++;
                    }
                }
            }
        }
        return holeCount >= 1 && holeCount <= 5;
    }
}

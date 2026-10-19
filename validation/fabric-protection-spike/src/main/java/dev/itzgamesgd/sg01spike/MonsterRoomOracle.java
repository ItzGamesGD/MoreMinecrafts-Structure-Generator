package dev.itzgamesgd.sg01spike;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.WorldGenRegion;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.levelgen.structure.BoundingBox;

/**
 * Experiment-only oracle (SG01_ORACLE=monster_room). Vanilla runs unguarded. The oracle reads the protected cells inside the maximal
 * footprint before the feature and again after it, and classifies the attempt by whether a non-air block was written into a protected
 * piece box. It intercepts no write, it only reads, and it never changes a decision.
 */
public final class MonsterRoomOracle {
    private static final ThreadLocal<Map<BlockPos, BlockState>> PENDING = new ThreadLocal<>();

    private MonsterRoomOracle() {
    }

    public static void begin(GuardStats stats, WorldGenLevel level, BlockPos origin) {
        PENDING.remove();
        stats.attempts.incrementAndGet();
        if (!(level instanceof WorldGenRegion region)) {
            stats.notWorldgen.incrementAndGet();
            return;
        }
        BoundingBox box = MonsterRoomGeometry.maxBox(origin);
        Probe.enter();
        try {
            List<BoundingBox> pieces = Guard.pieceBoxes(region, box);
            if (pieces == null) {
                stats.oracleUnknown.incrementAndGet();
                return;
            }
            Map<BlockPos, BlockState> before = new HashMap<>();
            for (BlockPos p : BlockPos.betweenClosed(box.minX(), box.minY(), box.minZ(), box.maxX(), box.maxY(), box.maxZ())) {
                for (BoundingBox piece : pieces) {
                    if (piece.isInside(p)) {
                        before.put(p.immutable(), region.getBlockState(p));
                        break;
                    }
                }
            }
            PENDING.set(before);
        } finally {
            Probe.exit();
        }
    }

    public static void end(GuardStats stats, WorldGenLevel level, BlockPos origin) {
        Map<BlockPos, BlockState> before = PENDING.get();
        PENDING.remove();
        if (before == null) return;
        int nonAir = 0;
        int changed = 0;
        for (Map.Entry<BlockPos, BlockState> e : before.entrySet()) {
            BlockState now = level.getBlockState(e.getKey());
            if (now.equals(e.getValue())) continue;
            changed++;
            if (!now.isAir()) nonAir++;
        }
        if (nonAir > 0) {
            stats.oracleNonAirWrite.incrementAndGet();
            stats.event(String.format("oracle monster_room origin=%d,%d,%d protected_cells=%d changed=%d non_air_writes=%d", origin.getX(), origin.getY(),
                    origin.getZ(), before.size(), changed, nonAir));
        } else {
            stats.oracleNoWrite.incrementAndGet();
        }
    }
}

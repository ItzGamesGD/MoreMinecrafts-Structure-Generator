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
 * Experiment-only oracle (SG01_ORACLE=monster_room). Vanilla runs unguarded. For every attempt the oracle records two decisions taken
 * before vanilla runs (the N7-A reach and the refined reach would cancel?) and the outcome after vanilla ran (did any block inside a
 * protected piece box change? did a non-air block change?). Each decision is then placed in a confusion matrix against the outcome.
 * It intercepts no write, it only reads, and it never changes an outcome.
 */
public final class MonsterRoomOracle {
    private record Pending(Map<BlockPos, BlockState> before, boolean refinedCancels, boolean n7aCancels) {
    }

    private static final ThreadLocal<Pending> PENDING = new ThreadLocal<>();

    private MonsterRoomOracle() {
    }

    public static void begin(GuardStats stats, WorldGenLevel level, BlockPos origin, List<BoundingBox> refinedReaches) {
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
            boolean refinedCancels = Guard.collides(level, refinedReaches);
            boolean n7aCancels = Guard.collides(level, List.of(box));
            Map<BlockPos, BlockState> before = new HashMap<>();
            for (BlockPos p : BlockPos.betweenClosed(box.minX(), box.minY(), box.minZ(), box.maxX(), box.maxY(), box.maxZ())) {
                for (BoundingBox piece : pieces) {
                    if (piece.isInside(p)) {
                        before.put(p.immutable(), region.getBlockState(p));
                        break;
                    }
                }
            }
            PENDING.set(new Pending(before, refinedCancels, n7aCancels));
        } finally {
            Probe.exit();
        }
    }

    public static void end(GuardStats stats, WorldGenLevel level, BlockPos origin) {
        Pending pending = PENDING.get();
        PENDING.remove();
        if (pending == null) return;
        int nonAir = 0;
        int changed = 0;
        for (Map.Entry<BlockPos, BlockState> e : pending.before().entrySet()) {
            BlockState now = level.getBlockState(e.getKey());
            if (now.equals(e.getValue())) continue;
            changed++;
            if (!now.isAir()) nonAir++;
        }
        boolean truth = changed > 0;
        if (nonAir > 0) {
            stats.oracleNonAirWrite.incrementAndGet();
            stats.event(String.format("oracle monster_room origin=%d,%d,%d protected_cells=%d changed=%d non_air_writes=%d refined=%s n7a=%s",
                    origin.getX(), origin.getY(), origin.getZ(), pending.before().size(), changed, nonAir, pending.refinedCancels(), pending.n7aCancels()));
        } else {
            stats.oracleNoWrite.incrementAndGet();
        }
        if (pending.refinedCancels()) {
            if (truth) stats.refinedTp.incrementAndGet();
            else stats.refinedFp.incrementAndGet();
        } else {
            if (truth) {
                stats.refinedFn.incrementAndGet();
                stats.event(String.format("FALSE NEGATIVE refined origin=%d,%d,%d changed=%d non_air=%d", origin.getX(), origin.getY(), origin.getZ(), changed, nonAir));
            } else {
                stats.refinedTn.incrementAndGet();
            }
        }
        if (pending.n7aCancels()) {
            if (truth) stats.n7aTp.incrementAndGet();
            else stats.n7aFp.incrementAndGet();
        } else {
            if (truth) stats.n7aFn.incrementAndGet();
            else stats.n7aTn.incrementAndGet();
        }
    }
}

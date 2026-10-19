package dev.itzgamesgd.sg01spike;

import it.unimi.dsi.fastutil.longs.LongSet;
import java.util.HashSet;
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

    public static final Mode MODE = parseMode();
    public static final GuardStats GEODE = new GuardStats("geode");
    public static final GuardStats MONSTER_ROOM = new GuardStats("monster_room");

    private Guard() {
    }

    private static Mode parseMode() {
        String value = System.getProperty("sg01.guard.mode", System.getenv("SG01_GUARD_MODE"));
        if (value == null || value.isBlank() || value.equalsIgnoreCase("enforce")) return Mode.ENFORCE;
        if (value.equalsIgnoreCase("observe")) return Mode.OBSERVE;
        throw new IllegalStateException("SG protection spike: unknown guard mode '" + value + "' (use observe or enforce)");
    }

    /** @return true if the feature instance must be cancelled (always false in OBSERVE mode, where the decision is only recorded). */
    public static boolean shouldCancel(GuardStats stats, WorldGenLevel level, BlockPos origin, BoundingBox reach) {
        stats.attempts.incrementAndGet();
        if (!(level instanceof WorldGenRegion region)) {
            stats.notWorldgen.incrementAndGet();
            return false;
        }
        Set<Structure> protectedSet = ProtectionConfig.protectedStructures();
        ChunkPos centre = region.getCenter();
        Set<Long> seenStarts = new HashSet<>();
        String verdict = null;
        String detail = "";
        boolean sawReference = false;
        int minCx = Math.max(reach.minX() >> 4, centre.x() - 1);
        int maxCx = Math.min(reach.maxX() >> 4, centre.x() + 1);
        int minCz = Math.max(reach.minZ() >> 4, centre.z() - 1);
        int maxCz = Math.min(reach.maxZ() >> 4, centre.z() + 1);
        scan:
        for (int cx = minCx; cx <= maxCx; cx++) {
            for (int cz = minCz; cz <= maxCz; cz++) {
                if (!region.hasChunk(cx, cz)) {
                    verdict = "unavailable";
                    detail = "chunk " + cx + "," + cz + " outside the step's cache";
                    break scan;
                }
                ChunkAccess chunk;
                Map<Structure, LongSet> references;
                try {
                    chunk = region.getChunk(cx, cz, ChunkStatus.STRUCTURE_REFERENCES);
                    references = chunk.getAllReferences();
                } catch (RuntimeException e) {
                    verdict = "unavailable";
                    detail = "references of chunk " + cx + "," + cz + ": " + e.getClass().getSimpleName();
                    break scan;
                }
                for (Map.Entry<Structure, LongSet> entry : references.entrySet()) {
                    if (!protectedSet.contains(entry.getKey())) continue;
                    sawReference = true;
                    for (long key : entry.getValue()) {
                        if (!seenStarts.add(key)) continue;
                        ChunkPos startPos = ChunkPos.unpack(key);
                        if (centre.getChessboardDistance(startPos) > ChunkStatus.MAX_STRUCTURE_DISTANCE || !region.hasChunk(startPos.x(), startPos.z())) {
                            verdict = "unavailable";
                            detail = "start chunk " + startPos.x() + "," + startPos.z() + " beyond readable distance";
                            break scan;
                        }
                        StructureStart start;
                        try {
                            start = region.getChunk(startPos.x(), startPos.z(), ChunkStatus.STRUCTURE_STARTS).getStartForStructure(entry.getKey());
                        } catch (RuntimeException e) {
                            verdict = "unavailable";
                            detail = "start chunk " + startPos.x() + "," + startPos.z() + ": " + e.getClass().getSimpleName();
                            break scan;
                        }
                        if (start == null || !start.isValid()) {
                            verdict = "unavailable";
                            detail = "referenced start at " + startPos.x() + "," + startPos.z() + " is " + (start == null ? "missing" : "invalid");
                            break scan;
                        }
                        int index = 0;
                        for (StructurePiece piece : start.getPieces()) {
                            if (piece.getBoundingBox().intersects(reach)) {
                                verdict = "collision";
                                detail = "start " + startPos.x() + "," + startPos.z() + " piece #" + index + " " + piece.getBoundingBox();
                                break scan;
                            }
                            index++;
                        }
                    }
                }
            }
        }
        if (verdict == null) {
            if (!sawReference) stats.fastPath.incrementAndGet();
            return false;
        }
        if (verdict.equals("collision")) stats.collisions.incrementAndGet();
        else stats.unavailable.incrementAndGet();
        stats.event(String.format("%s origin=%d,%d,%d centre=%d,%d reach=%s -> %s (%s)%s", stats.feature, origin.getX(), origin.getY(), origin.getZ(),
                centre.x(), centre.z(), reach, verdict, detail, MODE == Mode.ENFORCE ? " CANCELLED" : " observed"));
        if (verdict.equals("unavailable")) {
            SpikeMod.LOGGER.warn("SG_SPIKE unavailable structure data for {} at {}: {} (instance {})", stats.feature, origin, detail,
                    MODE == Mode.ENFORCE ? "cancelled" : "observed only");
        }
        if (MODE == Mode.ENFORCE) {
            stats.cancelled.incrementAndGet();
            return true;
        }
        stats.wouldCancel.incrementAndGet();
        return false;
    }
}

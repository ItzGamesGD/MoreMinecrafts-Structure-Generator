package dev.itzgamesgd.sgprotection;

/**
 * Chunk-coordinate rectangles ({@code {minX, minZ, maxX, maxZ}}, inclusive) of the area in which protection could not be established because structure
 * data was unavailable (N10-R). They are always clipped to the region's 3x3-chunk write zone, so the effect of an incident is bounded by nine chunk
 * columns. Pure Java (no Minecraft types), unit-tested directly.
 */
public final class UncertainFootprint {
    /** Vanilla bound on how far (in chunks) the pieces of a structure start can lie from the start chunk. */
    public static final int MAX_STRUCTURE_DISTANCE = 8;

    private UncertainFootprint() {
    }

    /** The write zone of a region centred on chunk (cx, cz). */
    public static int[] zone(int cx, int cz) {
        return new int[] {cx - 1, cz - 1, cx + 1, cz + 1};
    }

    /** Footprint of a chunk whose references could not be read: that chunk column, clipped to the zone. */
    public static int[] ofChunk(int chunkX, int chunkZ, int[] zone) {
        return clip(new int[] {chunkX, chunkZ, chunkX, chunkZ}, zone);
    }

    /** Footprint of a start that could not be read: everything within the vanilla piece distance of its chunk, clipped to the zone. Null if it cannot reach the zone. */
    public static int[] ofStart(int startX, int startZ, int[] zone) {
        return clip(new int[] {startX - MAX_STRUCTURE_DISTANCE, startZ - MAX_STRUCTURE_DISTANCE, startX + MAX_STRUCTURE_DISTANCE, startZ + MAX_STRUCTURE_DISTANCE}, zone);
    }

    /** Intersection of two rectangles, or null if they do not overlap. */
    public static int[] clip(int[] rect, int[] zone) {
        int minX = Math.max(rect[0], zone[0]);
        int minZ = Math.max(rect[1], zone[1]);
        int maxX = Math.min(rect[2], zone[2]);
        int maxZ = Math.min(rect[3], zone[3]);
        return minX > maxX || minZ > maxZ ? null : new int[] {minX, minZ, maxX, maxZ};
    }

    /** True if the block column (blockX, blockZ) lies in the rectangle. */
    public static boolean contains(int[] rect, int blockX, int blockZ) {
        int cx = blockX >> 4;
        int cz = blockZ >> 4;
        return cx >= rect[0] && cx <= rect[2] && cz >= rect[1] && cz <= rect[3];
    }

    /** Number of chunk columns in the rectangle. */
    public static int columns(int[] rect) {
        return (rect[2] - rect[0] + 1) * (rect[3] - rect[1] + 1);
    }
}

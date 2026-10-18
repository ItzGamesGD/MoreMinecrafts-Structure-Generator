package dev.itzgamesgd.sg01visual;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.ArrayDeque;
import java.util.Locale;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.minecraft.core.BlockPos;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.ai.navigation.PathNavigation;
import net.minecraft.world.entity.monster.zombie.Zombie;
import net.minecraft.world.level.Level;
import net.minecraft.world.phys.Vec3;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Test-only runtime traversal probe. A player-width mob (0.6 wide, same step height) is spawned at a start cell and
 * driven by Minecraft's own PathNavigation + MoveControl + JumpControl + entity collision toward a goal cell.
 * It is a collision/locomotion probe, NOT a live player or client input test.
 *
 * Request file (SG01_TRAVERSE_REQUEST), one leg per line: {@code id sx sy sz tx ty tz [timeoutTicks]} where (sx,sy,sz)
 * is the start feet cell and (tx,ty,tz) the goal feet cell. Results are appended to SG01_TRAVERSE_RESULT as JSON lines.
 */
public final class TraversalProbe implements ModInitializer {
    private static final Logger LOGGER = LoggerFactory.getLogger("sg01-traverse");

    /** Mob with every goal removed so only this probe controls movement. */
    private static final class ProbeZombie extends Zombie {
        ProbeZombie(Level level) {
            super(level);
            setPersistenceRequired();
        }

        /** Walk-only by default: SG01_TRAVERSE_ALLOW_JUMP=1 re-enables jumping (the mob otherwise hops on any 1.0 node rise). */
        @Override
        public void jumpFromGround() {
            if ("1".equals(System.getenv("SG01_TRAVERSE_ALLOW_JUMP"))) super.jumpFromGround();
        }

        @Override
        public boolean hurtServer(ServerLevel level, DamageSource source, float damage) {
            return false;
        }

        @Override
        protected void registerGoals() {
        }

    }

    private static final class Leg {
        String id;
        int[] start = new int[3];
        int[] goal = new int[3];
        int timeout = 900;
    }

    private final ArrayDeque<Leg> queue = new ArrayDeque<>();
    private Leg current;
    private ProbeZombie mob;
    private int ticks;
    private double maxY;
    private double minY;
    private boolean pathFound;
    private int pathLength;
    private int waited;

    @Override
    public void onInitialize() {
        ServerTickEvents.END_SERVER_TICK.register(this::tick);
    }

    private static Path requestPath() {
        String value = System.getenv("SG01_TRAVERSE_REQUEST");
        return value == null || value.isBlank() ? null : Path.of(value);
    }

    private void emit(String json) {
        String value = System.getenv("SG01_TRAVERSE_RESULT");
        if (value == null || value.isBlank()) return;
        try {
            Files.writeString(Path.of(value), json + "\n", StandardCharsets.UTF_8, StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (IOException e) {
            LOGGER.error("SG01_TRAVERSE_WRITE_FAILED", e);
        }
    }

    private void tick(MinecraftServer server) {
        ServerLevel level = server.overworld();
        if (current == null) {
            Path request = requestPath();
            if (request != null && Files.isRegularFile(request) && queue.isEmpty()) {
                try {
                    Path taken = request.resolveSibling(request.getFileName() + ".taken");
                    Files.move(request, taken, StandardCopyOption.REPLACE_EXISTING);
                    for (String line : Files.readAllLines(taken)) {
                        String[] p = line.trim().split("\\s+");
                        if (p.length < 7) continue;
                        Leg leg = new Leg();
                        leg.id = p[0];
                        for (int i = 0; i < 3; i++) {
                            leg.start[i] = Integer.parseInt(p[1 + i]);
                            leg.goal[i] = Integer.parseInt(p[4 + i]);
                        }
                        if (p.length > 7) leg.timeout = Integer.parseInt(p[7]);
                        queue.add(leg);
                    }
                    LOGGER.info("SG01_TRAVERSE_QUEUED {}", queue.size());
                } catch (IOException | NumberFormatException e) {
                    LOGGER.error("SG01_TRAVERSE_REQUEST_FAILED", e);
                }
            }
            if (queue.isEmpty()) return;
            if (!level.hasChunkAt(new BlockPos(queue.peek().start[0], queue.peek().start[1], queue.peek().start[2]))) return;
            current = queue.poll();
            mob = new ProbeZombie(level);
            mob.snapTo(current.start[0] + 0.5, current.start[1], current.start[2] + 0.5, 0.0F, 0.0F);
            level.addFreshEntity(mob);
            ticks = 0;
            waited = 0;
            maxY = minY = mob.getY();
            pathFound = false;
            pathLength = -1;
            return;
        }

        ticks++;
        // Let the mob settle onto the floor before it starts moving.
        if (ticks < 5) return;
        if (ticks == 5) {
            net.minecraft.world.level.pathfinder.Path path = mob.getNavigation()
                    .createPath(new BlockPos(current.goal[0], current.goal[1], current.goal[2]), 1);
            pathFound = path != null && path.canReach();
            pathLength = path == null ? -1 : path.getNodeCount();
        }
        maxY = Math.max(maxY, mob.getY());
        minY = Math.min(minY, mob.getY());
        Vec3 goal = new Vec3(current.goal[0] + 0.5, current.goal[1], current.goal[2] + 0.5);
        // PathNavigation ends a path once within about a block of the target, so accept a 2-block horizontal radius;
        // vertically the mob must be standing (on ground) at the goal level, so a mid-jump or a lower step does not count.
        boolean arrived = Math.hypot(mob.getX() - goal.x, mob.getZ() - goal.z) < 2.0 && mob.onGround() && Math.abs(mob.getY() - goal.y) < 0.3;
        if (arrived || ticks >= current.timeout || !mob.isAlive()) {
            emit(String.format(Locale.ROOT,
                    "{\"id\":\"%s\",\"result\":\"%s\",\"ticks\":%d,\"path_found_initial\":%b,\"path_nodes\":%d,\"start\":[%d,%d,%d],\"goal\":[%d,%d,%d],"
                            + "\"final\":[%.2f,%.2f,%.2f],\"min_y\":%.2f,\"max_y\":%.2f}",
                    current.id, arrived ? "PASS" : "FAIL", ticks, pathFound, pathLength, current.start[0], current.start[1], current.start[2],
                    current.goal[0], current.goal[1], current.goal[2], mob.getX(), mob.getY(), mob.getZ(), minY, maxY));
            LOGGER.info("SG01_TRAVERSE_{} {}", arrived ? "PASS" : "FAIL", current.id);
            mob.discard();
            mob = null;
            current = null;
            if (queue.isEmpty()) emit("{\"id\":\"__done__\"}");
            return;
        }
        PathNavigation nav = mob.getNavigation();
        if (nav.isDone() || ticks % 40 == 0) {
            nav.moveTo(goal.x, goal.y, goal.z, 1.0);
        }
    }
}

package dev.itzgamesgd.moreminecrafts.mmstprobe;

import dev.itzgamesgd.moreminecrafts.MoreMinecrafts;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import net.fabricmc.fabric.api.gametest.v1.CustomTestMethodInvoker;
import net.fabricmc.fabric.api.gametest.v1.GameTest;
import net.minecraft.commands.arguments.blocks.BlockStateParser;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.Identifier;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructurePlaceSettings;

/**
 * Throw-away MMB gametest, copied into a scratch clone by run_mmb_probe.sh and never committed to MMB.
 * Loads an MM-ST export through MMB's real resources, places it exactly as jigsaw worldgen does
 * (SinglePoolElement: knownShape, flags 18) and compares every cell with /mmst/expected.txt.
 */
public final class MmstExportProbeGameTests implements CustomTestMethodInvoker {
    @GameTest(maxTicks = 200)
    public void exportedTemplateLoadsAndPlacesExactly(GameTestHelper context) throws Exception {
        try (var reader = new BufferedReader(new InputStreamReader(
                getClass().getResourceAsStream("/mmst/expected.txt"), StandardCharsets.UTF_8))) {
            String[] header = reader.readLine().split(" ");  // "<id> <sx> <sy> <sz>"
            var id = Identifier.parse(header[0]);
            var level = context.getLevel();
            var template = level.getStructureTemplateManager().get(id);
            context.assertTrue(template.isPresent(), "template must load from MMB resources: " + id);
            var size = template.orElseThrow().getSize();
            context.assertTrue(size.getX() == Integer.parseInt(header[1]) && size.getY() == Integer.parseInt(header[2])
                    && size.getZ() == Integer.parseInt(header[3]), "unexpected template size " + size);
            BlockPos origin = context.absolutePos(BlockPos.ZERO).offset(24, 10, 0);
            var settings = new StructurePlaceSettings().setKnownShape(true);
            context.assertTrue(template.orElseThrow().placeInWorld(level, origin, origin, settings, RandomSource.create(0), 18),
                    "placeInWorld must succeed");
            int checked = 0;
            int mismatched = 0;
            String first = null;
            for (String line; (line = reader.readLine()) != null; ) {
                String[] parts = line.split(" ", 4);
                var pos = origin.offset(Integer.parseInt(parts[0]), Integer.parseInt(parts[1]), Integer.parseInt(parts[2]));
                var expected = BlockStateParser.parseForBlock(BuiltInRegistries.BLOCK, parts[3], false).blockState();
                checked++;
                if (!level.getBlockState(pos).equals(expected)) {
                    mismatched++;
                    if (first == null) first = line + " got " + level.getBlockState(pos);
                }
            }
            MoreMinecrafts.LOGGER.info("MMST_EXPORT_PROBE id={} size={} checked={} mismatched={} first={}", id, size, checked, mismatched, first);
            context.assertTrue(checked > 0 && mismatched == 0, "every cell must match: " + first);
        }
        context.succeed();
    }

    @Override
    public void invokeTestMethod(GameTestHelper context, Method method) throws ReflectiveOperationException {
        method.invoke(this, context);
    }
}

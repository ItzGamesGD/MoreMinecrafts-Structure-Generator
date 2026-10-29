// Prints, for every block state of the 26.x server, the facts vanilla's neighbour-connection code
// reads from a *neighbour* (WallBlock.connectsTo / FenceBlock.connectsTo / IronBarsBlock.attachsTo /
// WallBlock.updateShape / FenceGateBlock.updateShape), computed by the game's own code:
//   - isFaceSturdy(level, pos, side) for the four horizontal sides (SupportType.FULL, the default)
//   - the DOWN face of getCollisionShape(level, pos), tested with WallBlock's own private
//     TEST_SHAPE_POST / TEST_SHAPES_WALL exactly like WallBlock.isCovered
// and, per block, the classes the connection code tests with instanceof and
// Block.isExceptionForConnection. Block tags are not bound
// without a loaded datapack, so build_connectivity.py reads them from the jar's data/ instead.
// Run with the classes and bundled libraries of the unobfuscated server jar on the class path.
import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.EmptyBlockGetter;
import net.minecraft.world.level.block.FenceBlock;
import net.minecraft.world.level.block.FenceGateBlock;
import net.minecraft.world.level.block.IronBarsBlock;
import net.minecraft.world.level.block.WallBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.Property;
import net.minecraft.world.phys.shapes.BooleanOp;
import net.minecraft.world.phys.shapes.Shapes;
import net.minecraft.world.phys.shapes.VoxelShape;

import java.lang.reflect.Field;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class ConnectivityProbe {
    private static final Direction[] SIDES = {Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST};

    private static Object field(String name) throws Exception {
        Field f = WallBlock.class.getDeclaredField(name);
        f.setAccessible(true);
        return f.get(null);
    }

    private static boolean covered(VoxelShape above, VoxelShape test) {
        return !Shapes.joinIsNotEmpty(test, above, BooleanOp.ONLY_FIRST); // WallBlock.isCovered
    }

    private static <T extends Comparable<T>> String value(Property<T> property, BlockState state) {
        return property.getName(state.getValue(property)); // the serialized name, as in blocks.json
    }

    @SuppressWarnings("unchecked")
    public static void main(String[] args) throws Exception {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();
        VoxelShape post = (VoxelShape) field("TEST_SHAPE_POST");
        Map<Direction, VoxelShape> wall = (Map<Direction, VoxelShape>) field("TEST_SHAPES_WALL");
        var level = EmptyBlockGetter.INSTANCE;
        var pos = BlockPos.ZERO;
        System.out.println("MMST_DATA_VERSION " + SharedConstants.getCurrentVersion().dataVersion().version());
        for (var block : BuiltInRegistries.BLOCK) {
            String id = BuiltInRegistries.BLOCK.getKey(block).toString();
            List<String> kinds = new ArrayList<>();
            if (block instanceof WallBlock) kinds.add("wall");
            if (block instanceof FenceBlock) kinds.add("fence");
            if (block instanceof IronBarsBlock) kinds.add("bars");
            if (block instanceof FenceGateBlock) kinds.add("fence_gate");
            if (block.hasDynamicShape()) kinds.add("dynamic_shape");
            // Tags are unbound here, so this covers the instanceof/identity checks only; the
            // SHULKER_BOXES tag half of Block.isExceptionForConnection is added from the jar's data.
            if (net.minecraft.world.level.block.Block.isExceptionForConnection(block.defaultBlockState())) kinds.add("exception");
            System.out.println("MMST_BLOCK " + id + " " + (kinds.isEmpty() ? "-" : String.join(",", kinds)));
            for (BlockState state : block.getStateDefinition().getPossibleStates()) {
                StringBuilder props = new StringBuilder();
                for (Property<?> p : state.getProperties()) {
                    if (!props.isEmpty()) props.append(',');
                    props.append(p.getName()).append('=').append(value(p, state));
                }
                StringBuilder sturdy = new StringBuilder();
                for (Direction d : SIDES) sturdy.append(state.isFaceSturdy(level, pos, d) ? '1' : '0');
                VoxelShape down = state.getCollisionShape(level, pos).getFaceShape(Direction.DOWN);
                StringBuilder cover = new StringBuilder(covered(down, post) ? "1" : "0");
                for (Direction d : SIDES) cover.append(covered(down, wall.get(d)) ? '1' : '0');
                String offset = state.hasOffsetFunction() ? "offset" : "-";
                System.out.println("MMST_STATE " + id + " " + (props.isEmpty() ? "-" : props) + " " + sturdy + " " + cover + " " + offset);
            }
        }
        System.out.println("MMST_END");
    }
}

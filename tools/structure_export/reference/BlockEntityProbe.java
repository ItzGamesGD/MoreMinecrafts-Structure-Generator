// Prints the ids of every 26.x block that carries a block entity (implements EntityBlock).
// Run with the classes and bundled libraries of the unobfuscated server jar on the class path;
// build_reference.py does this. Output lines go through the server logger as "[STDOUT]: ...".
import net.minecraft.SharedConstants;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.block.EntityBlock;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class BlockEntityProbe {
    public static void main(String[] args) {
        SharedConstants.tryDetectVersion();
        Bootstrap.bootStrap();
        List<String> ids = new ArrayList<>();
        for (var block : BuiltInRegistries.BLOCK) {
            if (block instanceof EntityBlock) {
                ids.add(BuiltInRegistries.BLOCK.getKey(block).toString());
            }
        }
        Collections.sort(ids);
        System.out.println("MMST_DATA_VERSION " + SharedConstants.getCurrentVersion().dataVersion().version());
        System.out.println("MMST_BLOCK_ENTITY_BLOCKS " + String.join(",", ids));
    }
}

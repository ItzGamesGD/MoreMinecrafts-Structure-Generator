package dev.itzgamesgd.sg01spike.lab.mixin;

import java.util.List;
import java.util.Set;
import org.objectweb.asm.tree.ClassNode;
import org.spongepowered.asm.mixin.extensibility.IMixinConfigPlugin;
import org.spongepowered.asm.mixin.extensibility.IMixinInfo;

/** Lab only: applies the "foreign transformer" stand-in mixins when SG01_LAB_FOREIGN names their target (monster_room, geode or both). */
public final class LabMixinPlugin implements IMixinConfigPlugin {
    @Override
    public void onLoad(String mixinPackage) {
    }

    @Override
    public String getRefMapperConfig() {
        return null;
    }

    @Override
    public boolean shouldApplyMixin(String targetClassName, String mixinClassName) {
        String which = System.getenv("SG01_LAB_FOREIGN");
        if (mixinClassName.endsWith("ForeignMonsterRoomMixin")) return "monster_room".equals(which) || "both".equals(which);
        if (mixinClassName.endsWith("ForeignGeodeMixin")) return "geode".equals(which) || "both".equals(which);
        return true;
    }

    @Override
    public void acceptTargets(Set<String> myTargets, Set<String> otherTargets) {
    }

    @Override
    public List<String> getMixins() {
        return null;
    }

    @Override
    public void preApply(String targetClassName, ClassNode targetClass, String mixinClassName, IMixinInfo mixinInfo) {
    }

    @Override
    public void postApply(String targetClassName, ClassNode targetClass, String mixinClassName, IMixinInfo mixinInfo) {
    }
}

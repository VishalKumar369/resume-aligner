import React from "react";

/**
 * Animation-free stand-in for framer-motion.
 *
 * The real library resolves enter/exit animations on rAF, which makes "the
 * label is gone after collapsing" a race. Rendering plain DOM elements keeps
 * component tests about markup and behaviour rather than animation timing.
 */

// Props framer-motion consumes itself — passing them to a DOM node would only
// produce unknown-attribute warnings.
const MOTION_PROPS = new Set([
    "initial",
    "animate",
    "exit",
    "transition",
    "variants",
    "whileHover",
    "whileTap",
    "whileFocus",
    "whileDrag",
    "whileInView",
    "viewport",
    "layout",
    "layoutId",
    "drag",
    "onAnimationStart",
    "onAnimationComplete",
    "custom",
]);

const stripMotionProps = (props: Record<string, unknown>) => {
    const out: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(props)) {
        if (!MOTION_PROPS.has(key)) out[key] = value;
    }
    return out;
};

const componentCache = new Map<string, React.ElementType>();

const motionComponent = (tag: string) => {
    if (!componentCache.has(tag)) {
        const Component = React.forwardRef<unknown, Record<string, unknown>>((props, ref) =>
            React.createElement(tag, { ...stripMotionProps(props), ref })
        );
        Component.displayName = `motion.${tag}`;
        componentCache.set(tag, Component);
    }
    return componentCache.get(tag)!;
};

export const motion: Record<string, React.ElementType> = new Proxy(
    {},
    {
        get: (_target, tag: string) => motionComponent(tag),
    }
) as Record<string, React.ElementType>;

export const AnimatePresence = ({ children }: { children?: React.ReactNode }) => (
    <>{children}</>
);

export const useReducedMotion = () => false;
export const useAnimation = () => ({ start: () => Promise.resolve(), stop: () => {} });

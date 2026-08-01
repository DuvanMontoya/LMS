// @livekit/components-styles 1.2.0 publishes .css.d.ts files but its exports
// map points at .scss.d.ts. Keep these declarations local until upstream fixes
// the package metadata; runtime imports still use only public export subpaths.
declare module '@livekit/components-styles/components';
declare module '@livekit/components-styles/themes/default';

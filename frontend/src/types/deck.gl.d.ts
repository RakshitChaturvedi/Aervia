declare module '@deck.gl/react' {
  const DeckGL: any;
  export default DeckGL;
}

declare module '@deck.gl/layers' {
  export class ColumnLayer<T = any> {
    constructor(config: any);
  }
  export class ScatterplotLayer<T = any> {
    constructor(config: any);
  }
  export class TextLayer<T = any> {
    constructor(config: any);
  }
  export class PolygonLayer<T = any> {
    constructor(config: any);
  }
  export class BitmapLayer<T = any> {
    constructor(config: any);
  }
  export class IconLayer<T = any> {
    constructor(config: any);
  }
  export class PathLayer<T = any> {
    constructor(config: any);
  }
  export class GeoJsonLayer<T = any> {
    constructor(config: any);
  }
}

declare module '@deck.gl/core' {
  export class LightingEffect {
    constructor(config: any);
  }
  export class AmbientLight {
    constructor(config: any);
  }
  export class DirectionalLight {
    constructor(config: any);
  }
  export class FlyToInterpolator {
    constructor(config?: any);
  }
}


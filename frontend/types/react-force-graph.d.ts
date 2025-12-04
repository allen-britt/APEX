declare module "react-force-graph" {
  import type { ComponentType } from "react";

  export interface ForceGraphProps<N = any, L = any> {
    graphData: {
      nodes: N[];
      links: L[];
    };
    [key: string]: any;
  }

  export const ForceGraph2D: ComponentType<ForceGraphProps>;
}

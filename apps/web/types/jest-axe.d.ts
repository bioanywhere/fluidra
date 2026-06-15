declare module "jest-axe" {
  export interface AxeResults {
    violations: unknown[];
  }
  export function axe(
    html: Element | string,
    options?: Record<string, unknown>,
  ): Promise<AxeResults>;
  export const toHaveNoViolations: unknown;
}

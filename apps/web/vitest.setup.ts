import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Unmount React trees between tests (auto-cleanup isn't registered when vitest
// globals are disabled).
afterEach(() => cleanup());

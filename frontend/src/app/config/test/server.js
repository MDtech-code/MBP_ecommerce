import { setupServer } from "msw/node";

// Each integration test declares its own handlers. Unexpected HTTP is an error.
export const server = setupServer();

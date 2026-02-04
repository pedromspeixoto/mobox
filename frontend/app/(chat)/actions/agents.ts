"use server";

import { z } from "zod";
import { backend, BackendError } from "@/lib/api/backend";
import { AgentResponseSchema, type AgentResponse } from "@/lib/api/contracts";
import type { ActionResult } from "./types";

/**
 * Get all available agents
 * Backend: GET /api/v1/agents/
 */
export async function getAgents(): Promise<ActionResult<AgentResponse[]>> {
  try {
    const data = await backend.get<AgentResponse[]>("/agents/");
    const validatedData = z.array(AgentResponseSchema).parse(data);
    return { success: true, data: validatedData };
  } catch (error) {
    console.error("[getAgents] Error:", error);

    if (error instanceof BackendError) {
      return {
        success: false,
        error: error.message,
        code: error.statusCode,
      };
    }

    if (error instanceof z.ZodError) {
      console.error("[getAgents] Validation error:", error.errors);
      return { success: false, error: "Invalid response from server" };
    }

    return { success: false, error: "Failed to fetch agents" };
  }
}

/**
 * Get a specific agent by ID
 * Backend: GET /api/v1/agents/{agent_id}
 */
export async function getAgent(
  agentId: string
): Promise<ActionResult<AgentResponse>> {
  try {
    const data = await backend.get<AgentResponse>(`/agents/${agentId}`);
    const validatedData = AgentResponseSchema.parse(data);
    return { success: true, data: validatedData };
  } catch (error) {
    console.error(`[getAgent] Error for agent ${agentId}:`, error);

    if (error instanceof BackendError) {
      return {
        success: false,
        error: error.message,
        code: error.statusCode,
      };
    }

    if (error instanceof z.ZodError) {
      console.error("[getAgent] Validation error:", error.errors);
      return { success: false, error: "Invalid response from server" };
    }

    return { success: false, error: "Failed to fetch agent" };
  }
}

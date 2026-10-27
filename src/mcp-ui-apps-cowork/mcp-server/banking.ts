import { randomUUID } from "node:crypto";
import { z } from "zod";

export const wireSchema = z.object({
  id: z.string(),
  customer: z.string(),
  amount: z.number(),
  currency: z.string(),
  destination: z.string(),
  risk: z.number(),
  signals: z.array(z.string()),
});
export type Wire = z.infer<typeof wireSchema>;

export const holdInputSchema = z.object({
  wireId: z.string().min(1).max(64),
  reason: z.string().trim().min(1).max(1000).default("Analyst review from MCP App"),
});
export type HoldInput = z.infer<typeof holdInputSchema>;

export const holdSchema = z.object({
  holdRequestId: z.string(),
  wireId: z.string(),
  reason: z.string(),
  status: z.literal("PENDING_APPROVAL"),
  submittedAt: z.string(),
});
export type HoldRequest = z.infer<typeof holdSchema>;

const WIRES: Wire[] = [
  { id: "TX123", customer: "Contoso Corp", amount: 4_200_000, currency: "USD", destination: "KY", risk: 92,
    signals: ["New beneficiary", "Unusual amount", "High-risk destination"] },
  { id: "TX456", customer: "Fabrikam Ltd", amount: 2_100_000, currency: "USD", destination: "AE", risk: 87,
    signals: ["Velocity spike", "New beneficiary"] },
  { id: "TX789", customer: "Northwind Traders", amount: 8_700_000, currency: "USD", destination: "PA", risk: 84,
    signals: ["Round-dollar amount", "Shell-company indicators"] },
  { id: "TX901", customer: "Woodgrove Bank", amount: 350_000, currency: "USD", destination: "GB", risk: 41,
    signals: [] },
];

export interface BankingBackend {
  getWires(minRisk: number): Promise<Wire[]>;
  getWire(wireId: string): Promise<Wire | undefined>;
  createHold(input: HoldInput): Promise<HoldRequest>;
}

export const demoBanking: BankingBackend = {
  async getWires(minRisk) {
    return WIRES.filter((wire) => wire.risk >= minRisk).sort((a, b) => b.risk - a.risk);
  },
  async getWire(wireId) {
    return WIRES.find((wire) => wire.id === wireId);
  },
  async createHold({ wireId, reason }) {
    if (!await this.getWire(wireId)) throw new Error(`Unknown wire ${wireId}`);
    return {
      holdRequestId: `HOLD-${randomUUID()}`,
      wireId,
      reason,
      status: "PENDING_APPROVAL",
      submittedAt: new Date().toISOString(),
    };
  },
};

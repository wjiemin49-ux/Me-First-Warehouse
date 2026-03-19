import { DatabaseService } from "./database-service";
import { nowIso } from "@main/utils/time-utils";

export class AuditService {
  constructor(private readonly db: DatabaseService) {}

  record(input: {
    scriptId?: string;
    action: string;
    actor?: string;
    success: boolean;
    message?: string;
    payload?: Record<string, unknown>;
  }): void {
    this.db.run(
      `
      INSERT INTO operation_audit(script_id, action, actor, success, message, created_at, payload_json)
      VALUES(:scriptId, :action, :actor, :success, :message, :createdAt, :payloadJson)
      `,
      {
        scriptId: input.scriptId ?? null,
        action: input.action,
        actor: input.actor ?? "system",
        success: input.success ? 1 : 0,
        message: input.message ?? null,
        createdAt: nowIso(),
        payloadJson: JSON.stringify(input.payload ?? {}),
      },
    );
  }
}

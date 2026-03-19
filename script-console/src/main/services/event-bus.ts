import { EventEmitter } from "node:events";
import { APP_EVENTS } from "@shared/constants";
import { AppEventPayloadMap } from "@shared/types";

type AppEventName = (typeof APP_EVENTS)[keyof typeof APP_EVENTS];

export class EventBus {
  private readonly emitter = new EventEmitter();

  emit<K extends keyof AppEventPayloadMap>(event: K, payload: AppEventPayloadMap[K]): void {
    this.emitter.emit(event, payload);
  }

  on<K extends keyof AppEventPayloadMap>(event: K, listener: (payload: AppEventPayloadMap[K]) => void): () => void {
    this.emitter.on(event, listener);
    return () => this.emitter.off(event, listener);
  }

  removeAllListeners(): void {
    this.emitter.removeAllListeners();
  }
}

(function attachCoachingActivityTimer(root, factory) {
  const exported = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = exported;
  }
  root.CoachingActivityTimer = exported.CoachingActivityTimer;
})(typeof globalThis !== "undefined" ? globalThis : this, function createModule() {
  const DEFAULT_IDLE_TIMEOUT_MS = 7000;
  const DEFAULT_ANGLE_CHANGE_DEGREES = 4.5;
  const MAX_SAMPLE_GAP_MS = 2000;

  class CoachingActivityTimer {
    constructor(options = {}) {
      this.idleTimeoutMs = options.idleTimeoutMs || DEFAULT_IDLE_TIMEOUT_MS;
      this.angleChangeDegrees =
        options.angleChangeDegrees || DEFAULT_ANGLE_CHANGE_DEGREES;
      this.reset();
    }

    reset() {
      this.activeMilliseconds = 0;
      this.lastSampleAt = null;
      this.lastActivityAt = null;
      this.lastAngle = null;
      this.lastStage = null;
      this.lastCount = 0;
      this.suspended = false;
    }

    suspend() {
      this.suspended = true;
      this.lastSampleAt = null;
      this.lastActivityAt = null;
      this.lastAngle = null;
      this.lastStage = null;
    }

    resume() {
      this.suspended = false;
      this.lastSampleAt = null;
      this.lastActivityAt = null;
      this.lastAngle = null;
      this.lastStage = null;
    }

    static getAngle(status) {
      const candidates = [
        status.elbow_angle,
        status.average_elbow_angle,
        status.average_angle,
        status.average_knee_angle,
        status.knee_angle,
      ];
      const angle = candidates.map(Number).find(Number.isFinite);
      return angle === undefined ? null : angle;
    }

    update(status, now = Date.now(), enabled = true) {
      const poseUsable = Boolean(
        enabled
        && !this.suspended
        && (status?.person_detected ?? status?.person_valid)
        && status?.pose_valid
      );
      const angle = poseUsable ? CoachingActivityTimer.getAngle(status) : null;
      const stage = poseUsable && ![null, undefined, "UNKNOWN"].includes(status.stage)
        ? String(status.stage)
        : null;
      const count = Number(status?.count ?? this.lastCount);

      if (!poseUsable) {
        this.lastSampleAt = null;
        this.lastActivityAt = null;
        this.lastAngle = null;
        this.lastStage = null;
        if (Number.isFinite(count)) {
          this.lastCount = count;
        }
        return false;
      }

      const angleChanged = angle !== null
        && this.lastAngle !== null
        && Math.abs(angle - this.lastAngle) >= this.angleChangeDegrees;
      const stageChanged = stage !== null
        && this.lastStage !== null
        && stage !== this.lastStage;
      const countIncreased = Number.isFinite(count) && count > this.lastCount;
      const activitySignal = angleChanged || stageChanged || countIncreased;

      if (this.lastSampleAt !== null && this.lastActivityAt !== null) {
        const intervalStart = this.lastSampleAt;
        const intervalEnd = Math.min(now, this.lastActivityAt + this.idleTimeoutMs);
        const sampleGap = now - this.lastSampleAt;
        if (sampleGap >= 0 && sampleGap <= MAX_SAMPLE_GAP_MS && intervalEnd > intervalStart) {
          this.activeMilliseconds += intervalEnd - intervalStart;
        }
      }

      if (activitySignal) {
        this.lastActivityAt = now;
      }
      this.lastSampleAt = now;
      this.lastAngle = angle;
      this.lastStage = stage;
      if (Number.isFinite(count)) {
        this.lastCount = count;
      }
      return activitySignal;
    }

    getMilliseconds() {
      return Math.max(0, this.activeMilliseconds);
    }

    getWholeMinutes(repetitions) {
      if (Number(repetitions) <= 0) {
        return 0;
      }
      return Math.floor(this.getMilliseconds() / 60000);
    }
  }

  return { CoachingActivityTimer };
});

/**
 * Location and Geographic Distance Module for SyncPulse TypeScript Engine.
 *
 * Implements:
 * - Haversine straight-line distance calculation using Earth's mean radius = 6371.0 km.
 * - Missing coordinate detection ("Distance unavailable").
 * - Browser Geolocation API wrapper with explicit permission states.
 * - Authorised manual entry / correction validation.
 * - Strict labeling: "straight-line distance", never road distance or travel time.
 */

export const EARTH_RADIUS_KM = 6371.0;

export interface CoordinatesTS {
  latitude: number;
  longitude: number;
  accuracy_m?: number | null;
  source?: "GPS_CAPTURE" | "MANUAL_ENTRY";
  captured_at?: string;
}

export type GeolocationStatus =
  | "unsupported"
  | "idle"
  | "requesting"
  | "granted"
  | "denied"
  | "timeout"
  | "error";

export function isValidCoordinate(
  lat: number | null | undefined,
  lon: number | null | undefined
): boolean {
  if (lat === null || lat === undefined || lon === null || lon === undefined) {
    return false;
  }
  if (typeof lat !== "number" || typeof lon !== "number") {
    return false;
  }
  if (isNaN(lat) || isNaN(lon)) {
    return false;
  }
  return lat >= -90.0 && lat <= 90.0 && lon >= -180.0 && lon <= 180.0;
}

/**
 * Calculates approximate straight-line distance locally between two points
 * using the Haversine formula with Earth's mean radius approx 6371 km.
 *
 * Returns distance in kilometers (rounded to 2 decimal places), or null if coordinates are missing.
 */
export function haversineDistanceKm(
  lat1: number | null | undefined,
  lon1: number | null | undefined,
  lat2: number | null | undefined,
  lon2: number | null | undefined
): number | null {
  if (!isValidCoordinate(lat1, lon1) || !isValidCoordinate(lat2, lon2)) {
    return null;
  }

  const toRad = (deg: number) => (deg * Math.PI) / 180.0;

  const phi1 = toRad(lat1!);
  const phi2 = toRad(lat2!);
  const deltaPhi = toRad(lat2! - lat1!);
  const deltaLambda = toRad(lon2! - lon1!);

  const a =
    Math.sin(deltaPhi / 2.0) ** 2 +
    Math.cos(phi1) * Math.cos(phi2) * Math.sin(deltaLambda / 2.0) ** 2;

  const clampedA = Math.min(1.0, Math.max(0.0, a));
  const c = 2.0 * Math.atan2(Math.sqrt(clampedA), Math.sqrt(1.0 - clampedA));
  const distance = EARTH_RADIUS_KM * c;

  return Math.round(distance * 100) / 100;
}

/**
 * Formats distance with honest clinical labeling.
 * Explicitly denotes straight-line distance; never infers travel time or road distance.
 */
export function formatDistanceLabel(distanceKm: number | null | undefined): string {
  if (distanceKm === null || distanceKm === undefined) {
    return "Distance unavailable";
  }

  if (distanceKm < 1.0) {
    const meters = Math.round(distanceKm * 1000);
    return `${meters} m (straight-line)`;
  }
  return `${distanceKm.toFixed(2)} km (straight-line)`;
}

/**
 * Captures current worker position via HTML5 Geolocation API.
 * Prompts user for permission only upon explicit action.
 */
export function captureWorkerLocation(
  onSuccess: (coords: CoordinatesTS) => void,
  onError: (status: GeolocationStatus, message: string) => void
): void {
  if (typeof window === "undefined" || !("geolocation" in navigator)) {
    onError("unsupported", "GPS access is not supported by this browser/device.");
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const lat = position.coords.latitude;
      const lon = position.coords.longitude;
      const acc = position.coords.accuracy;

      if (!isValidCoordinate(lat, lon)) {
        onError("error", "Captured coordinates were outside valid geographic bounds.");
        return;
      }

      onSuccess({
        latitude: Math.round(lat * 1000000) / 1000000,
        longitude: Math.round(lon * 1000000) / 1000000,
        accuracy_m: Math.round(acc * 10) / 10,
        source: "GPS_CAPTURE",
        captured_at: new Date().toISOString(),
      });
    },
    (err) => {
      if (err.code === err.PERMISSION_DENIED) {
        onError("denied", "Location permission was denied. You can enter coordinates manually.");
      } else if (err.code === err.TIMEOUT) {
        onError("timeout", "GPS signal acquisition timed out. Please try again or enter manually.");
      } else {
        onError("error", `Location acquisition failed: ${err.message}`);
      }
    },
    {
      enableHighAccuracy: true,
      timeout: 12000,
      maximumAge: 30000,
    }
  );
}

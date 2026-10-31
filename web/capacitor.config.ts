import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "org.syncpulse.fieldos",
  appName: "SyncPulse",
  webDir: "dist",
  server: {
    androidScheme: "https",
    cleartext: false,
  },
  plugins: {
    LocalNotifications: {
      smallIcon: "ic_stat_icon_config_sample",
      iconColor: "#047857",
    },
  },
};

export default config;

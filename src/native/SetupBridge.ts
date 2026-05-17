import { NativeModules } from 'react-native';
const { ServerModule } = NativeModules;

export const setupCloudflared = (): Promise<string> =>
  ServerModule.setupCloudflared();

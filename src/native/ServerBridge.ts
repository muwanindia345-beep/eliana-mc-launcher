import { NativeModules, NativeEventEmitter } from 'react-native';

const { ServerModule } = NativeModules;
const emitter = new NativeEventEmitter(ServerModule);

export interface ServerConfig {
  jarPath: string;
  serverDir: string;
  javaPath?: string;
  ramMb?: number;
}

export const ServerBridge = {
  startServer: (config: ServerConfig): Promise<string> =>
    ServerModule.startServer(config),

  stopServer: (): Promise<string> =>
    ServerModule.stopServer(),

  sendCommand: (cmd: string): Promise<string> =>
    ServerModule.sendCommand(cmd),

  startTunnel: (token: string): Promise<string> =>
    ServerModule.startTunnel(token),

  getStatus: (): Promise<string> =>
    ServerModule.getStatus(),

  getTunnelUrl: (): Promise<string> =>
    ServerModule.getTunnelUrl(),

  getLogs: (): Promise<string[]> =>
    ServerModule.getLogs(),

  onLog: (cb: (line: string) => void) =>
    emitter.addListener('onLog', cb),

  onStatusChange: (cb: (status: string) => void) =>
    emitter.addListener('onStatusChange', cb),

  onTunnelUrl: (cb: (url: string) => void) =>
    emitter.addListener('onTunnelUrl', cb),
};

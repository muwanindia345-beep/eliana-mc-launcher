import React, { useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity,
  StatusBar, ToastAndroid, Alert,
} from 'react-native';
import { ServerBridge } from './src/native/ServerBridge';
import { NativeModules } from 'react-native';

const { UpdateModule } = NativeModules;
const CURRENT_VERSION = '1.0.0';
const VERSION_URL = 'https://raw.githubusercontent.com/saad890/eliana-mc-launcher/main/version.txt';
const APK_URL = 'https://github.com/saad890/eliana-mc-launcher/releases/latest/download/eliana.apk';

const JAR_PATH   = '/sdcard/minecraft/server.jar';
const SERVER_DIR = '/sdcard/minecraft';
const JAVA_PATH  = '/data/data/com.termux/files/usr/bin/java';

export default function App() {
  const [status, setStatus]       = useState('stopped');
  const [tunnelUrl, setTunnelUrl] = useState('');
  const [players, setPlayers]     = useState('0');
  const [updating, setUpdating]   = useState(false);

  useEffect(() => {
    const l1 = ServerBridge.onStatusChange(s => setStatus(s));
    const l2 = ServerBridge.onTunnelUrl(url => setTunnelUrl(url));
    const l3 = ServerBridge.onLog(line => {
      const m = line.match(/There are (\d+) of a max/);
      if (m) setPlayers(m[1]);
    });
    checkForUpdate();
    return () => { l1.remove(); l2.remove(); l3.remove(); };
  }, []);

  const checkForUpdate = async () => {
    try {
      const latest = await UpdateModule.checkUpdate(VERSION_URL);
      if (latest && latest !== CURRENT_VERSION) {
        ToastAndroid.show(`Update available: v${latest}`, ToastAndroid.LONG);
      }
    } catch (_) {}
  };

  const handleUpdate = async () => {
    try {
      const latest = await UpdateModule.checkUpdate(VERSION_URL);
      if (latest === CURRENT_VERSION) {
        ToastAndroid.show('Already up to date!', ToastAndroid.SHORT);
        return;
      }
      Alert.alert(
        'Update Available',
        `New version v${latest} available!\nDownload now?`,
        [
          { text: 'Cancel', style: 'cancel' },
          {
            text: 'Update', onPress: async () => {
              setUpdating(true);
              ToastAndroid.show('Downloading update...', ToastAndroid.SHORT);
              try {
                await UpdateModule.downloadAndInstall(APK_URL);
              } catch (e: any) {
                Alert.alert('Error', e.message);
              }
              setUpdating(false);
            }
          }
        ]
      );
    } catch (e: any) {
      Alert.alert('Error', 'Could not check for updates');
    }
  };

  const handleLaunch = async () => {
    if (status === 'running') {
      await ServerBridge.stopServer();
    } else if (status === 'stopped') {
      try {
        await ServerBridge.startServer({
          jarPath: JAR_PATH,
          serverDir: SERVER_DIR,
          javaPath: JAVA_PATH,
          ramMb: 512,
        });
      } catch (e: any) {
        Alert.alert('Error', e.message);
      }
    }
  };

  const statusColor =
    status === 'running'  ? '#4CAF50' :
    status === 'starting' ? '#FF9800' :
    status === 'stopping' ? '#FF5722' : '#F44336';

  const menuItems = [
    {
      icon: '🌐',
      label: 'CLOUDFLARE TUNNEL',
      sub: tunnelUrl ? tunnelUrl.replace('https://','') : 'Not connected',
      onPress: () => {
        if (tunnelUrl) {
          ToastAndroid.show(tunnelUrl, ToastAndroid.LONG);
        } else {
          ServerBridge.startTunnel('');
          ToastAndroid.show('Starting tunnel...', ToastAndroid.SHORT);
        }
      }
    },
    {
      icon: '👥',
      label: 'PLAYER LIST',
      sub: `${players} online`,
      onPress: () => {
        ServerBridge.sendCommand('list');
        ToastAndroid.show(`${players} players online`, ToastAndroid.SHORT);
      }
    },
    {
      icon: '📁',
      label: 'SERVER DIRECTORY',
      sub: SERVER_DIR,
      onPress: () => ToastAndroid.show(SERVER_DIR, ToastAndroid.SHORT),
    },
    {
      icon: '🔄',
      label: updating ? 'DOWNLOADING...' : 'CHECK FOR UPDATE',
      sub: `Current: v${CURRENT_VERSION}`,
      onPress: handleUpdate,
    },
  ];

  return (
    <View style={s.root}>
      <StatusBar backgroundColor="#1a1a1a" barStyle="light-content"/>

      {/* Header */}
      <View style={s.header}>
        <View>
          <Text style={s.appName}>ElianaMC Launcher</Text>
          <Text style={s.version}>v{CURRENT_VERSION}</Text>
        </View>
        <View style={s.statusBadge}>
          <View style={[s.dot, {backgroundColor: statusColor}]}/>
          <Text style={[s.statusText, {color: statusColor}]}>
            {status.toUpperCase()}
          </Text>
        </View>
      </View>

      {/* Server card */}
      <View style={s.serverCard}>
        <View style={s.serverIcon}>
          <Text style={s.serverIconText}>⛏</Text>
        </View>
        <View style={{flex:1}}>
          <Text style={s.serverName}>Minecraft Server</Text>
          <Text style={s.serverSub}>PaperMC · 512MB · Java</Text>
        </View>
      </View>

      {/* Menu */}
      <View style={s.menu}>
        {menuItems.map((item, i) => (
          <TouchableOpacity key={i} style={s.menuItem} onPress={item.onPress}>
            <Text style={s.menuIcon}>{item.icon}</Text>
            <View style={{flex:1}}>
              <Text style={s.menuLabel}>{item.label}</Text>
              <Text style={s.menuSub} numberOfLines={1}>{item.sub}</Text>
            </View>
            <Text style={s.menuArrow}>›</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Launch button */}
      <View style={s.bottom}>
        <TouchableOpacity
          style={[s.launchBtn, status === 'running' && s.stopBtn, status === 'starting' && s.startingBtn]}
          onPress={handleLaunch}
          disabled={status === 'starting' || status === 'stopping'}
        >
          <Text style={s.launchText}>
            {status === 'running'  ? '⏹  STOP SERVER'  :
             status === 'starting' ? '⏳  STARTING...'  :
             status === 'stopping' ? '⏳  STOPPING...'  : '▶  LAUNCH'}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex:1, backgroundColor:'#121212' },
  header: { flexDirection:'row', justifyContent:'space-between', alignItems:'center',
    paddingHorizontal:20, paddingTop:16, paddingBottom:12,
    borderBottomWidth:1, borderBottomColor:'#2a2a2a' },
  appName: { color:'#fff', fontSize:20, fontWeight:'800' },
  version: { color:'#666', fontSize:11, marginTop:2 },
  statusBadge: { flexDirection:'row', alignItems:'center', gap:6,
    backgroundColor:'#1e1e1e', paddingHorizontal:12, paddingVertical:6, borderRadius:20 },
  dot: { width:8, height:8, borderRadius:4 },
  statusText: { fontSize:12, fontWeight:'700' },
  serverCard: { flexDirection:'row', alignItems:'center', margin:16,
    backgroundColor:'#1e1e1e', borderRadius:14, padding:16, gap:14 },
  serverIcon: { width:52, height:52, borderRadius:12, backgroundColor:'#2a2a2a',
    alignItems:'center', justifyContent:'center' },
  serverIconText: { fontSize:26 },
  serverName: { color:'#fff', fontSize:16, fontWeight:'700' },
  serverSub: { color:'#666', fontSize:12, marginTop:3 },
  menu: { flex:1, paddingHorizontal:16, gap:2 },
  menuItem: { flexDirection:'row', alignItems:'center', backgroundColor:'#1e1e1e',
    borderRadius:12, paddingHorizontal:16, paddingVertical:14, gap:14, marginBottom:4 },
  menuIcon: { fontSize:22, width:32, textAlign:'center' },
  menuLabel: { color:'#fff', fontSize:14, fontWeight:'600' },
  menuSub: { color:'#555', fontSize:11, marginTop:2 },
  menuArrow: { color:'#444', fontSize:22, fontWeight:'300' },
  bottom: { padding:16, paddingBottom:24 },
  launchBtn: { backgroundColor:'#1976D2', paddingVertical:18,
    borderRadius:14, alignItems:'center' },
  stopBtn: { backgroundColor:'#C62828' },
  startingBtn: { backgroundColor:'#E65100' },
  launchText: { color:'#fff', fontSize:17, fontWeight:'900', letterSpacing:2 },
});

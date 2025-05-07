/**
 * 这是一个桥接文件，用于解决从 $lib/stores.ts 导入的问题
 * 重新导出 stores/index.ts 中的所有内容
 */

export * from './stores/index'; 
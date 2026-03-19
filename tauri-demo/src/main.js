import { open } from '@tauri-apps/api/dialog';
import { invoke } from '@tauri-apps/api/tauri';

// 测试 IPC 通信
window.testIPC = async () => {
  const status = document.getElementById('status');
  status.innerHTML = '<p>状态：发送消息中...</p>';
  
  try {
    const response = await invoke('greet', { name: 'Tauri' });
    status.innerHTML = `<p>状态：收到响应</p><p>消息：${response}</p>`;
  } catch (error) {
    status.innerHTML = `<p>状态：错误</p><p>错误：${error.message}</p>`;
  }
};

// 打开文件对话框
window.openFile = async () => {
  try {
    const selected = await open({
      multiple: false,
      filters: [
        { name: '文本文件', extensions: ['txt'] },
        { name: '所有文件', extensions: ['*'] }
      ]
    });
    
    if (selected) {
      const fileInfo = document.getElementById('fileInfo');
      const filePath = document.getElementById('filePath');
      
      fileInfo.style.display = 'block';
      filePath.textContent = selected;
    }
  } catch (error) {
    console.error('打开文件失败:', error);
  }
};

// 页面加载完成后初始化
window.addEventListener('DOMContentLoaded', () => {
  console.log('Tauri 示例应用已加载');
});
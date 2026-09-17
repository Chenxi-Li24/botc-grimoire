import { useEffect, useState } from 'react'
import Join from './Join'
import Storyteller from './Storyteller'

// 极简 hash 路由:'#/storyteller' 说书人控制台,其余走玩家加入页
export default function App() {
  const [hash, setHash] = useState(location.hash)

  useEffect(() => {
    const onChange = () => setHash(location.hash)
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])

  return hash.startsWith('#/storyteller') ? <Storyteller /> : <Join />
}

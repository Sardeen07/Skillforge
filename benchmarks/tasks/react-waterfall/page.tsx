import { Button, Card, Spinner } from '@/components'
import { getUser, getOrders, getRecommendations } from '@/lib/api'

export default async function ProfilePage({ params }: { params: { id: string } }) {
  const user = await getUser(params.id)
  const orders = await getOrders(params.id)
  const recs = await getRecommendations(params.id)

  function OrderRow({ order }: { order: { id: string; total: number } }) {
    return (
      <Card>
        <span>{order.id}</span>
        <span>{order.total}</span>
      </Card>
    )
  }

  if (!user) return <Spinner />

  return (
    <div>
      <h1>{user.name}</h1>
      {orders.map((o) => (
        <OrderRow key={o.id} order={o} />
      ))}
      <ul>
        {recs.map((r) => (
          <li key={r.id}>{r.title}</li>
        ))}
      </ul>
      <Button>Reorder</Button>
    </div>
  )
}

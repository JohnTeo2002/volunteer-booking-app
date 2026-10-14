import { Card, Layout, Menu, Typography } from 'antd';

import Dashboard from './components/Dashboard';
import SlotList from './components/SlotList';
import { useSlots } from './hooks/useSlots';

const { Header, Content } = Layout;

function Navigation({ activeKey }: { activeKey: 'volunteer' | 'admin' }) {
  return (
    <Header
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 28,
        paddingInline: 24,
        background: '#ffffff',
        borderBottom: '1px solid #f0f0f0',
      }}
    >
      <Typography.Text strong style={{ color: '#1677ff', whiteSpace: 'nowrap' }}>
        Food Bank Volunteers
      </Typography.Text>
      <Menu
        mode="horizontal"
        selectedKeys={[activeKey]}
        style={{ flex: 1, minWidth: 0, borderBottom: 0 }}
        items={[
          { key: 'volunteer', label: <a href="/">Volunteer booking</a> },
          { key: 'admin', label: <a href="/admin">Admin dashboard</a> },
        ]}
      />
    </Header>
  );
}

function VolunteerPage() {
  const { slots } = useSlots();

  return (
    <>
      <Navigation activeKey="volunteer" />
      <Content style={{ padding: 24, maxWidth: 1100, width: '100%', margin: '0 auto' }}>
        <Card>
          <Typography.Title level={1}>Find a volunteer shift</Typography.Title>
          <Typography.Paragraph type="secondary">
            Choose a date and time that works for you. Slots that are full cannot be booked.
          </Typography.Paragraph>
          <SlotList slots={slots} />
        </Card>
      </Content>
    </>
  );
}

function AdminPage() {
  const { slots, lastUpdated, isStale } = useSlots();

  return (
    <>
      <Navigation activeKey="admin" />
      <Content style={{ padding: 24, maxWidth: 1200, width: '100%', margin: '0 auto' }}>
        <Dashboard slots={slots} lastUpdated={lastUpdated} isStale={isStale} />
      </Content>
    </>
  );
}

export default function App() {
  const isAdminRoute = window.location.pathname.replace(/\/$/, '') === '/admin';

  return (
    <Layout style={{ minHeight: '100vh', background: '#f5f7fb' }}>
      {isAdminRoute ? <AdminPage /> : <VolunteerPage />}
    </Layout>
  );
}

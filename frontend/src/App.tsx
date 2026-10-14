import { Card, Divider, Typography } from 'antd';

import Dashboard from './components/Dashboard';
import SlotList from './components/SlotList';

export default function App() {
  return (
    <div
      style={{
        padding: 24,
        maxWidth: 1200,
        margin: '0 auto',
      }}
    >
      <Card>
        <Typography.Title level={1}>Food Bank Volunteer Booking</Typography.Title>
        <Typography.Paragraph>
          View live capacity, look up a booking as an admin, or book an available volunteer slot.
        </Typography.Paragraph>
        <Dashboard />
        <Divider />
        <SlotList />
      </Card>
    </div>
  );
}

import React from 'react';
import { Card, Typography } from 'antd';
import SlotList from './components/SlotList';

export default function App() {
  return (
    <div style={{ padding: 24, maxWidth: 960, margin: '0 auto' }}>
      <Card>
        <Typography.Title level={2}>Food Bank Volunteer Booking</Typography.Title>
        <Typography.Paragraph>
          Choose an available volunteer slot. Full slots cannot be booked.
        </Typography.Paragraph>
        <SlotList />
      </Card>
    </div>
  );
}

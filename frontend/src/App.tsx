import React from 'react';
import { Card, Typography } from 'antd';

export default function App() {
  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <Card>
        <Typography.Title level={2}>Food Bank Volunteer Booking</Typography.Title>
        <Typography.Paragraph>
          Frontend scaffolding is ready. Connects to FastAPI backend.
        </Typography.Paragraph>
      </Card>
    </div>
  );
}

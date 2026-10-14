import { useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Form,
  Input,
  Row,
  Space,
  Statistic,
  Typography,
} from 'antd';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { fetchBooking } from '../api/client';
import { ApiError, type Booking, type Slot } from '../types/api';


interface LookupFields {
  booking_id: string;
}

function getLookupError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === 'UNAUTHORIZED') {
      return 'Access denied. Check the admin token and try again.';
    }
    if (error.code === 'BOOKING_NOT_FOUND') {
      return 'No booking was found with that ID.';
    }
    return error.message;
  }
  return 'Could not contact the API. Make sure the backend is running and try again.';
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

interface DashboardProps {
  slots: Slot[];
  lastUpdated: string | null;
  isStale: boolean;
}

export default function Dashboard({ slots, lastUpdated, isStale }: DashboardProps) {
  const [adminToken, setAdminToken] = useState('');
  const [booking, setBooking] = useState<Booking | null>(null);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const totalCapacity = slots.reduce((sum, slot) => sum + slot.capacity, 0);
  const totalBooked = slots.reduce((sum, slot) => sum + slot.booked, 0);
  const totalRemaining = slots.reduce((sum, slot) => sum + slot.remaining, 0);
  const chartData = slots.map((slot: Slot) => ({
    slotLabel: `${slot.date.slice(5)} ${slot.start_time}`,
    booked: slot.booked,
    capacity: slot.capacity,
  }));

  const handleLookup = async (fields: LookupFields) => {
    const bookingId = Number(fields.booking_id);
    if (!Number.isSafeInteger(bookingId) || bookingId < 1) {
      setLookupError('Enter a valid positive booking ID.');
      setBooking(null);
      return;
    }

    setLoading(true);
    setBooking(null);
    setLookupError(null);
    try {
      const result = await fetchBooking(bookingId, adminToken);
      setBooking(result);
    } catch (error: unknown) {
      setLookupError(getLookupError(error));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Space direction="vertical" size="large" style={{ display: 'flex' }}>
      <div>
        <Typography.Title level={2} style={{ marginBottom: 4 }}>
          Admin dashboard
        </Typography.Title>
        <Typography.Paragraph type="secondary" style={{ marginBottom: 0 }}>
          A live overview of volunteer slots and a quick booking lookup for the demo.
        </Typography.Paragraph>
      </div>

      {isStale && (
        <Alert
          type="warning"
          showIcon
          message="Slot data may be out of date"
          description="The latest refresh failed. Statistics and chart show the last successfully loaded data."
        />
      )}

      <Row gutter={[16, 16]}>
        <Col xs={12} md={6}>
          <Card><Statistic title="Volunteer slots" value={slots.length} /></Card>
        </Col>
        <Col xs={12} md={6}>
          <Card><Statistic title="Total capacity" value={totalCapacity} /></Card>
        </Col>
        <Col xs={12} md={6}>
          <Card><Statistic title="Booked spots" value={totalBooked} /></Card>
        </Col>
        <Col xs={12} md={6}>
          <Card><Statistic title="Spots remaining" value={totalRemaining} /></Card>
        </Col>
      </Row>

      <Card
        title="Booked vs capacity"
        extra={
          <Typography.Text type="secondary">
            Last updated: {lastUpdated ?? 'Waiting for first update'}
          </Typography.Text>
        }
      >
        {chartData.length === 0 ? (
          <Empty description="No slots available yet. Start the backend and run seed.py." />
        ) : (
          <div style={{ width: '100%', height: 320 }}>
            <ResponsiveContainer>
              <BarChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 44 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="slotLabel"
                  angle={-25}
                  textAnchor="end"
                  interval={0}
                  height={64}
                />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Legend />
                <Bar dataKey="booked" name="Booked" fill="#1677ff" radius={[4, 4, 0, 0]} />
                <Bar dataKey="capacity" name="Capacity" fill="#b7c9e2" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </Card>

      <Card title="Find a booking" extra={<Typography.Text type="secondary">Admin only</Typography.Text>}>
        <Typography.Paragraph type="secondary">
          Enter your admin token and a booking ID to view the stored booking. The token is kept
          only in this page's memory and is never saved in browser storage.
        </Typography.Paragraph>
        <Form<LookupFields>
          layout="vertical"
          onFinish={handleLookup}
          initialValues={{ booking_id: '1' }}
        >
          <Form.Item label="Admin token" required>
            <Input.Password
              autoComplete="off"
              value={adminToken}
              onChange={(event) => setAdminToken(event.target.value)}
              placeholder="Enter ADMIN_TOKEN"
            />
          </Form.Item>
          <Form.Item
            label="Booking ID"
            name="booking_id"
            rules={[
              { required: true, message: 'Enter a booking ID.' },
              { pattern: /^[1-9]\d*$/, message: 'Enter a positive whole number.' },
            ]}
          >
            <Input inputMode="numeric" placeholder="e.g. 1" />
          </Form.Item>
          {lookupError && (
            <Alert
              type="error"
              showIcon
              message={lookupError}
              style={{ marginBottom: 16 }}
            />
          )}
          <Button
            type="primary"
            htmlType="submit"
            loading={loading}
            disabled={!adminToken.trim() || loading}
          >
            Look up booking
          </Button>
        </Form>

        {booking && (
          <Descriptions
            title={`Booking #${booking.id}`}
            bordered
            column={{ xs: 1, sm: 2 }}
            style={{ marginTop: 24 }}
          >
            <Descriptions.Item label="Slot ID">{booking.slot_id}</Descriptions.Item>
            <Descriptions.Item label="Created">{formatDateTime(booking.created_at)}</Descriptions.Item>
            <Descriptions.Item label="Volunteer">{booking.volunteer_name}</Descriptions.Item>
            <Descriptions.Item label="Email">{booking.email}</Descriptions.Item>
            <Descriptions.Item label="Phone">{booking.phone}</Descriptions.Item>
          </Descriptions>
        )}
      </Card>
    </Space>
  );
}

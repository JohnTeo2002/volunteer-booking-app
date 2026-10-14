import { useState } from 'react';
import { Alert, Button, Space, Table, Tag, Typography } from 'antd';
import type { TableColumnsType } from 'antd';
import type { Slot } from '../types/api';
import BookingForm from './BookingForm';

interface SlotListProps {
  slots: Slot[];
  lastUpdated: string | null;
  isStale: boolean;
}

export default function SlotList({ slots, lastUpdated, isStale }: SlotListProps) {
  const [selectedSlot, setSelectedSlot] = useState<Slot | null>(null);

  const columns: TableColumnsType<Slot> = [
    {
      title: 'Date',
      dataIndex: 'date',
      key: 'date',
    },
    {
      title: 'Time',
      key: 'time',
      render: (_, slot) => (
        <span>
          {slot.start_time} – {slot.end_time}
        </span>
      ),
    },
    {
      title: 'Remaining spots',
      dataIndex: 'remaining',
      key: 'remaining',
      render: (remaining: number) =>
        remaining === 0 ? <Tag color="red">Full</Tag> : remaining,
    },
    {
      title: 'Action',
      key: 'action',
      render: (_, slot) => (
        <Space>
          <Button
            type="primary"
            disabled={slot.remaining === 0}
            onClick={() => setSelectedSlot(slot)}
          >
            Book
          </Button>
        </Space>
      ),
    },
  ];

  const handleBookingSuccess = () => {
    setSelectedSlot(null);
  };

  return (
    <section aria-labelledby="available-slots-heading">
      <Typography.Title level={3} id="available-slots-heading">
        Available volunteer slots
      </Typography.Title>
      {isStale && (
        <Alert
          type="warning"
          showIcon
          message="Slot data may be out of date"
          description="We couldn't refresh the slots. Showing the most recently loaded data."
          style={{ marginBottom: 16 }}
        />
      )}
      <Typography.Paragraph type="secondary">
        Last updated: {lastUpdated ?? 'Waiting for first update'}
      </Typography.Paragraph>
      <Table<Slot>
        rowKey="id"
        columns={columns}
        dataSource={slots}
        pagination={false}
        locale={{ emptyText: 'No volunteer slots available' }}
      />
      {selectedSlot && (
        <BookingForm
          key={selectedSlot.id}
          slot={selectedSlot}
          open
          onCancel={() => setSelectedSlot(null)}
          onSuccess={handleBookingSuccess}
        />
      )}
    </section>
  );
}

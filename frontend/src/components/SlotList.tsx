import { Button, Space, Table, Tag, Typography } from 'antd';
import type { TableColumnsType } from 'antd';
import type { Slot } from '../types/api';

const MOCK_SLOTS: Slot[] = [
  {
    id: 1,
    event_id: 1,
    date: '2026-10-17',
    start_time: '09:00',
    end_time: '12:00',
    capacity: 10,
    booked: 6,
    remaining: 4,
  },
  {
    id: 2,
    event_id: 1,
    date: '2026-10-17',
    start_time: '13:00',
    end_time: '16:00',
    capacity: 8,
    booked: 8,
    remaining: 0,
  },
  {
    id: 3,
    event_id: 2,
    date: '2026-10-18',
    start_time: '09:00',
    end_time: '12:00',
    capacity: 6,
    booked: 2,
    remaining: 4,
  },
  {
    id: 4,
    event_id: 2,
    date: '2026-10-18',
    start_time: '13:00',
    end_time: '16:00',
    capacity: 12,
    booked: 12,
    remaining: 0,
  },
];

export default function SlotList() {
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
          <Button type="primary" disabled={slot.remaining === 0}>
            Book
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <section aria-labelledby="available-slots-heading">
      <Typography.Title level={3} id="available-slots-heading">
        Available volunteer slots
      </Typography.Title>
      <Table<Slot>
        rowKey="id"
        columns={columns}
        dataSource={MOCK_SLOTS}
        pagination={false}
        locale={{ emptyText: 'No volunteer slots available' }}
      />
    </section>
  );
}

import { useState } from 'react';
import { Alert, Button, Form, Input, Modal, Space, Typography, message } from 'antd';
import type { BookingRequest, Slot } from '../types/api';
import { ApiError } from '../types/api';
import { createBooking } from '../api/client';

interface BookingFormProps {
  slot: Slot;
  open: boolean;
  onCancel: () => void;
  onSuccess: () => void;
}

interface BookingFields {
  volunteer_name: string;
  email: string;
  phone: string;
}

function friendlyError(error: unknown): { title: string; description: string } {
  if (error instanceof ApiError) {
    if (error.code === 'SLOT_FULL') {
      return {
        title: 'This slot is full',
        description: 'Someone else may have taken the remaining spot. Please choose another slot.',
      };
    }
    if (error.code === 'DUPLICATE_BOOKING') {
      return {
        title: 'You have already booked this slot',
        description: error.message,
      };
    }
    return { title: 'Booking failed', description: error.message };
  }
  return {
    title: 'Unable to submit your booking',
    description: 'Please check your connection and try again.',
  };
}

export default function BookingForm({
  slot,
  open,
  onCancel,
  onSuccess,
}: BookingFormProps) {
  const [form] = Form.useForm<BookingFields>();
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<{ title: string; description: string } | null>(null);

  const handleSubmit = async (fields: BookingFields) => {
    setSubmitting(true);
    setErrorMessage(null);

    const request: BookingRequest = {
      slot_id: slot.id,
      volunteer_name: fields.volunteer_name.trim(),
      email: fields.email.trim().toLowerCase(),
      phone: fields.phone.trim(),
    };

    try {
      await createBooking(request);
      message.success('Booking confirmed!');
      form.resetFields();
      onSuccess();
    } catch (error: unknown) {
      setErrorMessage(friendlyError(error));
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = () => {
    if (submitting) return;
    setErrorMessage(null);
    form.resetFields();
    onCancel();
  };

  return (
    <Modal
      title="Book a volunteer slot"
      open={open}
      onCancel={handleCancel}
      footer={null}
      destroyOnClose
      closable={!submitting}
      maskClosable={!submitting}
    >
      <Typography.Paragraph type="secondary">
        {slot.date} · {slot.start_time}–{slot.end_time}
      </Typography.Paragraph>

      {errorMessage && (
        <Alert
          type="error"
          showIcon
          message={errorMessage.title}
          description={errorMessage.description}
          style={{ marginBottom: 16 }}
        />
      )}

      <Form<BookingFields>
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        requiredMark
      >
        <Form.Item
          label="Name"
          name="volunteer_name"
          rules={[
            { required: true, whitespace: true, message: 'Please enter your name.' },
            { max: 100, message: 'Name must be 100 characters or fewer.' },
          ]}
        >
          <Input autoComplete="name" maxLength={100} />
        </Form.Item>

        <Form.Item
          label="Email"
          name="email"
          rules={[
            { required: true, whitespace: true, message: 'Please enter your email.' },
            { type: 'email', message: 'Enter a valid email address.' },
            { max: 254, message: 'Email must be 254 characters or fewer.' },
          ]}
        >
          <Input autoComplete="email" maxLength={254} />
        </Form.Item>

        <Form.Item
          label="Phone"
          name="phone"
          rules={[
            { required: true, whitespace: true, message: 'Please enter your phone number.' },
            {
              pattern: /^(?=(?:\D*\d){7})[0-9+() .-]{7,20}$/,
              message: 'Use 7–20 allowed characters and at least 7 digits.',
            },
          ]}
        >
          <Input autoComplete="tel" maxLength={20} />
        </Form.Item>

        <Space style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <Button onClick={handleCancel} disabled={submitting}>
            Cancel
          </Button>
          <Button type="primary" htmlType="submit" loading={submitting} disabled={submitting}>
            Confirm booking
          </Button>
        </Space>
      </Form>
    </Modal>
  );
}

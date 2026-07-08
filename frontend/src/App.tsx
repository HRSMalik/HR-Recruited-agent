import { useState } from 'react'
import {
  PageBanner,
  Button,
  Badge,
  Card,
  CardHeader,
  CardBody,
  CardFooter,
  SectionHeader,
  Input,
  Select,
  Table,
  AlertBanner,
  Modal,
} from './components'

// Temporary component gallery — verifies the BL-FE-02 library.
// Replaced by the app shell + routes in BL-FE-04.
export default function App() {
  const [open, setOpen] = useState(false)
  return (
    <div style={{ padding: 32, maxWidth: 980, display: 'flex', flexDirection: 'column', gap: 24 }}>
      <PageBanner
        title="Component library"
        subtitle="BL-FE-02 — shared kit, growth-green, SVG icons"
        actions={<Button icon="plus">New job post</Button>}
      />

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <Button>Primary</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="ghost" icon="rerank">Re-rank</Button>
        <Button variant="danger">Reject</Button>
        <Button size="sm" icon="check">Confirm</Button>
        <Button disabled>Disabled</Button>
      </div>

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <Badge variant="strong">Strong yes</Badge>
        <Badge variant="yes">Yes</Badge>
        <Badge variant="review" icon="flag">Review</Badge>
        <Badge variant="no">No</Badge>
        <Badge variant="neutral">Draft</Badge>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Card>
          <CardHeader>
            <SectionHeader title="Fields" subtitle="label + error" />
          </CardHeader>
          <CardBody>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <Input label="Full name" placeholder="Amara Okafor" />
              <Select
                label="Recommendation"
                options={[
                  { value: 'strong', label: 'Strong yes' },
                  { value: 'yes', label: 'Yes' },
                  { value: 'review', label: 'Review' },
                ]}
              />
              <Input label="Email" defaultValue="not-an-email" error="Enter a valid email address" />
            </div>
          </CardBody>
          <CardFooter>
            <Button onClick={() => setOpen(true)}>Open modal</Button>
            <Button variant="ghost">Cancel</Button>
          </CardFooter>
        </Card>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <AlertBanner variant="info">AI drafted criteria — confirm before they lock.</AlertBanner>
          <AlertBanner variant="success">Criteria confirmed for Senior Backend Engineer.</AlertBanner>
          <AlertBanner variant="warning">3 calls are awaiting a retry decision.</AlertBanner>
          <AlertBanner variant="danger">Booking token expired — reissue to continue.</AlertBanner>
        </div>
      </div>

      <Card>
        <CardHeader>
          <SectionHeader title="Table" subtitle="ranked candidates" />
        </CardHeader>
        <Table>
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Composite</th>
              <th>Recommendation</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Amara Okafor</td>
              <td className="num">90</td>
              <td><Badge variant="strong">Strong yes</Badge></td>
            </tr>
            <tr>
              <td>Lucas Bianchi</td>
              <td className="num">73</td>
              <td><Badge variant="review" icon="flag">Review</Badge></td>
            </tr>
          </tbody>
        </Table>
      </Card>

      <Modal
        open={open}
        title="Confirm criteria"
        onClose={() => setOpen(false)}
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
            <Button icon="check" onClick={() => setOpen(false)}>Confirm</Button>
          </>
        }
      >
        Scoring locks to these weights once confirmed. Candidates aren't scored until then.
      </Modal>
    </div>
  )
}

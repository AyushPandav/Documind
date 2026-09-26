import { DocumentItem, ChatMessage, CitationSource } from '@/types';

export const INITIAL_DOCUMENTS: DocumentItem[] = [
  {
    id: 'doc-1',
    name: 'employee_handbook.pdf',
    pages: 42,
    size: '2.4 MB',
    status: 'INDEXED',
    uploadedAt: 'Today, 09:15 AM',
  },
  {
    id: 'doc-2',
    name: 'company_policy.pdf',
    pages: 18,
    size: '1.1 MB',
    status: 'INDEXED',
    uploadedAt: 'Today, 09:30 AM',
  },
  {
    id: 'doc-3',
    name: 'annual_report.pdf',
    pages: 86,
    size: '5.8 MB',
    status: 'PROCESSING',
    progress: 72,
    uploadedAt: 'Today, 10:05 AM',
  },
];

export const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: 'msg-1',
    role: 'user',
    content: 'What is the refund policy?',
    timestamp: '10:12 AM',
  },
  {
    id: 'msg-2',
    role: 'assistant',
    content: 'The refund period is 30 days from the purchase date [1]. Certain exceptions apply for custom enterprise deployments and consulting services [2].',
    timestamp: '10:12 AM',
    citations: [
      {
        id: 'cite-1',
        index: 1,
        documentId: 'doc-2',
        documentName: 'company_policy.pdf',
        page: 12,
        snippet: 'Refund requests must be submitted within 30 days of initial purchase. All requests require proof of payment and are issued to the original payment method within 5-7 business days.',
        relevance: 94,
      },
      {
        id: 'cite-2',
        index: 2,
        documentId: 'doc-2',
        documentName: 'company_policy.pdf',
        page: 14,
        snippet: 'Enterprise software configurations, dedicated instance provisioning fees, and custom development packages are strictly non-refundable once the onboarding period commences.',
        relevance: 87,
      },
    ],
  },
];

export interface MockAnswer {
  keywords: string[];
  answer: string;
  citations?: CitationSource[];
  isInsufficientInfo?: boolean;
}

export const MOCK_KNOWLEDGE_BASE: MockAnswer[] = [
  {
    keywords: ['refund', 'return', 'money back'],
    answer: 'The refund period is 30 days from the purchase date [1]. Certain exceptions apply for custom enterprise deployments and consulting services [2].',
    citations: [
      {
        id: 'cite-refund-1',
        index: 1,
        documentId: 'doc-2',
        documentName: 'company_policy.pdf',
        page: 12,
        snippet: 'Refund requests must be submitted within 30 days of initial purchase. All requests require proof of payment and are issued to the original payment method within 5-7 business days.',
        relevance: 94,
      },
      {
        id: 'cite-refund-2',
        index: 2,
        documentId: 'doc-2',
        documentName: 'company_policy.pdf',
        page: 14,
        snippet: 'Enterprise software configurations, dedicated instance provisioning fees, and custom development packages are strictly non-refundable once the onboarding period commences.',
        relevance: 87,
      },
    ],
  },
  {
    keywords: ['leave', 'vacation', 'holiday', 'pto', 'days of leave'],
    answer: 'Employees are entitled to 24 days of annual leave [1]. Leave requests must be submitted through the internal portal at least 2 weeks in advance [2].',
    citations: [
      {
        id: 'cite-leave-1',
        index: 1,
        documentId: 'doc-1',
        documentName: 'employee_handbook.pdf',
        page: 8,
        snippet: 'Full-time team members accrue standard annual paid leave at a rate of 2.0 days per calendar month, totaling 24 days per fiscal year.',
        relevance: 96,
      },
      {
        id: 'cite-leave-2',
        index: 2,
        documentId: 'doc-1',
        documentName: 'employee_handbook.pdf',
        page: 9,
        snippet: 'Planned vacation time exceeding 3 consecutive business days must be logged via the DocuMind People Portal at least 14 days prior to commencement.',
        relevance: 89,
      },
    ],
  },
  {
    keywords: ['requirement', 'requirements', 'compliance', 'security', 'audit'],
    answer: 'Key compliance requirements include mandatory multi-factor authentication [1], bi-annual SOC2 audit participation [2], and adhering to secure credential rotation policies [3].',
    citations: [
      {
        id: 'cite-req-1',
        index: 1,
        documentId: 'doc-1',
        documentName: 'employee_handbook.pdf',
        page: 22,
        snippet: 'All workstation endpoints and cloud services require hardware-backed or authenticator app multi-factor verification. SMS verification is explicitly prohibited.',
        relevance: 92,
      },
      {
        id: 'cite-req-2',
        index: 2,
        documentId: 'doc-1',
        documentName: 'employee_handbook.pdf',
        page: 25,
        snippet: 'Engineering and operations personnel must preserve deployment logs and participate in bi-annual SOC2 Type II compliance audits without exception.',
        relevance: 88,
      },
      {
        id: 'cite-req-3',
        index: 3,
        documentId: 'doc-2',
        documentName: 'company_policy.pdf',
        page: 7,
        snippet: 'API keys, service account credentials, and master database connection strings must be rotated every 90 days or immediately following staff role alterations.',
        relevance: 81,
      },
    ],
  },
  {
    keywords: ['overtime', 'working hours', 'schedule'],
    answer: 'Standard working hours are 40 hours per week [1]. Overtime must be pre-approved by department leads and is compensated at 1.5x regular pay [2].',
    citations: [
      {
        id: 'cite-work-1',
        index: 1,
        documentId: 'doc-1',
        documentName: 'employee_handbook.pdf',
        page: 4,
        snippet: 'Core working hours operate between 09:00 and 17:00 local time Monday through Friday, with flexible asynchronous overlap encouraged.',
        relevance: 93,
      },
      {
        id: 'cite-work-2',
        index: 2,
        documentId: 'doc-1',
        documentName: 'employee_handbook.pdf',
        page: 6,
        snippet: 'Non-exempt overtime hours must receive written pre-authorization from the direct engineering manager and are remunerated at standard statutory premium rates.',
        relevance: 85,
      },
    ],
  },
];

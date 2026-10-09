import { records, requireAuth } from '../../../lib/data';

export async function GET(request: Request) {
  // SHADOWLAB_FIX: authentication
  return Response.json(records['alice-record']);
}

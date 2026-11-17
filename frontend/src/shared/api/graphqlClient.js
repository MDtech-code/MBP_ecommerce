import { ApolloClient, InMemoryCache, createHttpLink } from "@apollo/client";
import { API_BASE_URL } from "@shared/config";

const graphqlUri = `${API_BASE_URL}/graphql/`;

if (import.meta.env.DEV) {
  console.log("[GraphQL:Client] Configured URI:", graphqlUri);
}

const httpLink = createHttpLink({
  uri: graphqlUri,
});

export const client = new ApolloClient({
  link: httpLink,
  cache: new InMemoryCache(),
});
